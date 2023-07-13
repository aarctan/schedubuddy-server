import random
import re, os, sqlite3, json, time
import string
import sys
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from pathlib import Path

enum_weekday = {'M': 0, 'T': 1, 'W': 2, 'H': 3, 'F': 4, 'S': 5, 'U': 6}
term_start_dates = {}
year_str = str(datetime.now().year)

def days_in_date_range(day, range_start, range_end):
    # Returns a list of dates that a 'day', e.g. 'M', occurs in the range of dates
    weekday = enum_weekday[day]
    d_s = datetime.strptime(range_start, '%Y-%m-%d')
    d_e = datetime.strptime(range_end, '%Y-%m-%d')
    dates = []
    for d_ord in range(d_s.toordinal(), d_e.toordinal() + 1):
        d = date.fromordinal(d_ord)
        if (d.weekday() == weekday):
            dates.append(d)
    return set(dates)


def is_valid_key(k):
    """
    key = (day of week, start time, end time, location)
    the first 3 should never be None, that's what this function verifies
    """
    return None not in k[:3]


def process_and_write(raw_class_obj, db_cursor):
    # Retrieve the raw keys of the object
    termId = raw_class_obj["term"]
    termName = raw_class_obj["termName"]
    subject = raw_class_obj["subject"].replace('_', ' ')
    catalog = raw_class_obj["catalog"]
    courseId = f"{subject} {catalog}"
    classId = raw_class_obj["classId"]
    component = raw_class_obj["component"]
    section = raw_class_obj["section"]
    embeds = raw_class_obj["embeds"]
    instructionMode = "Online" if raw_class_obj.get("online") else "In Person"

    # Exit if this class has already been written
    db_cursor.execute("SELECT * FROM uOfAClass WHERE term=? AND course=? AND class=?", (termId, courseId, classId))
    if db_cursor.fetchone():
        return

    # Try to figure out the instructors, class times, etc
    # For class times, suppose we find that a class occurs on day D in location L
    # from time S to E. To write this class time in the db, we need to
    # check that the class time (D, S, E, L) occurs at least 4 times.
    # We can map (D, S, E, L) to a list of dates it occurs and check count.
    # 7/11/2023: exempt DSEL>=4 check if D is on the weekend.
    instructors = []
    dsel_dates_map = {}
    potentially_biweekly = True

    # Range of dates, e.g. "2022-01-05 - 2022-04-08 MWF 12:00 - 12:50 (CCIS L2-190)"
    # It's possible for there to be multiple ranges, in which case we need to create
    # classtimes for all of them. Also possible to see single date and time, e.g. "2022-01-19 18:00 - 20:50 (TBD)"
    # the mega-regex takes care of all of this. In re.VERBOSE mode, whitespace is ignore unless escape, and comments
    # can be made with hashtags
    mega_regex = re.compile(r"""
        # start date should always be present ex '2022-01-19 '
        (?P<start_d>\d+-\d+-\d+)
        # The end date and days are not always present but when they are they'll look like this ' - 2022-04-08 MWF'
        (\ -\ (?P<end_d>\d+-\d+-\d+)\ (?P<days>\w+))?\ 
        # start time should always be present ex '12:00 - '
        (?P<start_t>\d+:\d+)\ -\ 
        # end time should always be present ex '12:50'
        (?P<end_t>\d+:\d+)
        # location will not always be present, but when it is it'll look like this: ' (CCIS L2-190)'
        (\ \((?P<location>.*?)\))?
    """, re.VERBOSE)

    for em in embeds:
        em = em.replace('\n', ' ')
        if re.search("^Primary Instructor: \w+", em):
            instructor = em.partition("Primary Instructor: ")[2]
            if "Co-Instructor" in instructor:
                instructor = instructor[:instructor.find("Co-Instructor")].rstrip()
            elif "Instructor" in instructor:
                instructor = instructor[:instructor.find("Instructor")].rstrip().rsplit(' ', 1)[0].rstrip()
            instructors.append(instructor)
        else:
            for parsed in mega_regex.finditer(em):
                p = parsed.groupdict()
                keys = []
                # ie, location is assigned if it's not None or TBD
                location = p["location"] if p["location"] not in (None, "TBD") else None
                if not p["end_d"]:
                    # Single date and time, e.g. "2022-01-19 18:00 - 20:50 (TBD)"
                    # indicates we're dealing with a single date and time
                    class_date = datetime.strptime(p["start_d"], "%Y-%m-%d")
                    class_day = "MTWHFSU"[class_date.weekday()]
                    key = (class_day, p["start_t"], p["end_t"], location)
                    assert is_valid_key(key)
                    dsel_dates_map.setdefault(key, set()).add(class_date)
                else:
                    # "normal" date ranges
                    potentially_biweekly = False
                    for day in p["days"]:
                        key = (day, p["start_t"], p["end_t"], location)
                        assert is_valid_key(key)
                        dsel_dates_map.setdefault(key, set()).update(days_in_date_range(day, p["start_d"], p["end_d"]))

    instructors = str(instructors) if instructors != [] else None
    if len(dsel_dates_map) == 0:
        # if the current year is in any of the embeds, we likely failed to parse a date here, so lets warn about that
        assert not any(map(lambda x: year_str in x, embeds)), f"The current year is in at least one embed, date parsing failure? {embeds=}"

    # only write courses we know the schedules for
    # Write the term if it does not exist
    db_cursor.execute("INSERT OR IGNORE INTO uOfATerm VALUES (?, ?, ?, ?)", (termId, termName, None, None))

    # Write a new course for the term if it does not exist
    db_cursor.execute("SELECT * FROM uOfACourse WHERE term=? AND course=?", (termId, courseId))
    if not db_cursor.fetchone():
        db_cursor.execute(
            "INSERT INTO uOfACourse VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (termId, courseId, subject, catalog, courseId, None, None, None, None, None, None, None, None, None)
        )

    for dsel in dsel_dates_map:
        if len(dsel_dates_map[dsel]) >= 4 or dsel[0] in ('S', 'U'):
            biweekly = None
            if potentially_biweekly and str(termId) in term_start_dates:
                biweekly = True
                datetimes = sorted(list(dsel_dates_map[dsel]))
                for i in range(len(datetimes) - 1):
                    dt1, dt2 = datetimes[i], datetimes[i + 1]
                    if (dt2 - dt1).days < 14:
                        biweekly = None
                if biweekly:  # check if biweekly flag is 1 or 2
                    biweekly = 1 if (datetimes[0] - term_start_dates[str(termId)]).days <= 7 else 2
            # biweekly = None # temporarily disable biweekly classes
            day, start_t, end_t, location = dsel
            start_t = time.strftime("%I:%M %p", time.strptime(start_t, '%H:%M'))
            end_t = time.strftime("%I:%M %p", time.strptime(end_t, '%H:%M'))
            query = "INSERT INTO uOfAClassTime Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db_cursor.execute(query, (termId, courseId, classId, location, None, None,
                                      day, start_t, end_t, biweekly))

    # Write a new class for this course
    query = "INSERT INTO uOfAClass Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,\
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    db_cursor.execute(query, (termId, courseId, classId, component, section,
                              f"{courseId} {component} {section}",
                              instructors, None, "ONLINE" if instructionMode == "Internet" else None,
                              None, None, None, None, None, None, None, None, None, None, None, None,
                              None, None, instructionMode, None, None))


def initialize_db(db_cursor):
    db_cursor.execute(f"CREATE TABLE uOfATerm(term TEXT UNIQUE, termTitle TEXT,\
    startDate TEXT, endDate TEXT)")
    db_cursor.execute(f"CREATE TABLE uOfACourse(term TEXT, course TEXT,\
    subject TEXT, catalog TEXT, asString TEXT, units TEXT, courseTitle TEXT,\
    subjectTitle TEXT, courseDescription TEXT, career TEXT, faculty TEXT,\
    facultyCode TEXT, department TEXT, departmentCode TEXT)")
    db_cursor.execute(f"CREATE TABLE uOfAClass(term TEXT, course TEXT,\
    class TEXT, component TEXT, section TEXT, asString TEXT, instructorUid TEXT,\
    campus TEXT, location TEXT, capacity TEXT, classStatus TEXT, classNotes TEXT,\
    classType TEXT, consent TEXT, startDate TEXT, endDate TEXT, enrollStatus TEXT,\
    gradingBasis TEXT, examStatus TEXT, examDate TEXT, examStartTime TEXT,\
    examEndTime TEXT, autoEnroll TEXT, instructionMode TEXT, session TEXT, units TEXT)")
    db_cursor.execute(f"CREATE TABLE uOfAClassTime(term TEXT, course TEXT,\
    class TEXT, location TEXT, startDate TEXT, endDate TEXT, day TEXT, startTime TEXT,\
    endTime TEXT, biweekly TEXT)")


def retrieve_term_start_dates():
    # Assume that (biweekly) labs do not occur on the first week. Therefore, they
    # must start on the monday after the first week. All labs during this week
    # are assumed to have a biweekly flag of 1, and ones that start the week
    # after the first week of labs will have a biweekly flag of 2.

    # first day of fall in catalog:
    # "Fall Term and Fall/Winter two-term classes begin. Exceptions may apply; students must consult with their Faculty office."
    # first day of winter in catalog:
    # "Winter Term classes begin. Exceptions may apply; students must consult with their Faculty office."
    fall_first = datetime.strptime("September 5, 2023", '%B %d, %Y')
    winter_first = datetime.strptime("January 8, 2024", '%B %d, %Y')
    term_start_dates["1850"] = fall_first + timedelta((0 - fall_first.weekday()) % 7)
    term_start_dates["1860"] = winter_first + timedelta((0 - winter_first.weekday()) % 7)

def db_update():
    dirname = Path(__file__).parent
    default_db_path = dirname / "../local/cataloguedb.db"
    default_raw_path = dirname / "../local/raw.json"

    parser = ArgumentParser()
    parser.add_argument("--db", '-d', help="database path. overwrites if it exists already", default=default_db_path)
    parser.add_argument("--raw", "-r", help="raw.json path", default=default_raw_path)
    args = parser.parse_args()
    db_path = Path(args.db).resolve()
    raw_path = Path(args.raw).resolve()
    print(f"Using db path: {db_path}")
    print(f"Using raw.json path: {raw_path}")

    if db_path.is_dir():
        print("please specify a file for db, not directory")
        sys.exit()

    if db_path.exists():
        print("warning: existing db file will be overwritten at the end of import process")

    final_db_path = db_path
    # we will first write the new db, then replace the old file with this file
    # this gives us one last chance to not accidentally overwrite the existing file :)
    db_path = db_path.parent / f"{db_path.name}.temp.{''.join(random.choices(string.ascii_lowercase, k=6))}"

    with open(raw_path) as raw_fp:
        data = json.load(raw_fp)

    db_conn = sqlite3.connect(db_path)
    db_cursor = db_conn.cursor()
    initialize_db(db_cursor)
    retrieve_term_start_dates()
    for raw_class_obj in data:
        process_and_write(raw_class_obj, db_cursor)

    db_conn.commit()
    db_conn.close()
    db_path.rename(final_db_path)


db_update()
