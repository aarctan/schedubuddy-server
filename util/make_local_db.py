import random
import re, os, sqlite3, json, time
import string
import sys
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from pathlib import Path

enum_weekday = {'M': 0, 'T': 1, 'W': 2, 'H': 3, 'F': 4, 'S': 5, 'U': 6}
term_start_dates = {}


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
    instructionMode = "Online" if raw_class_obj["online"] else "In Person"

    # Write the term if it does not exist
    db_cursor.execute("INSERT OR IGNORE INTO uOfATerm VALUES (?, ?, ?, ?)", (termId, termName, None, None))

    # Write a new course for the term if it does not exist
    db_cursor.execute("SELECT * FROM uOfACourse WHERE term=? AND course=?", (termId, courseId))
    if not db_cursor.fetchone():
        db_cursor.execute(
            "INSERT INTO uOfACourse VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (termId, courseId, subject, catalog, courseId, None, None, None, None, None, None, None, None, None)
        )

    # Exit if this class has already been written
    db_cursor.execute("SELECT * FROM uOfAClass WHERE term=? AND course=? AND class=?", (termId, courseId, classId))
    if db_cursor.fetchone():
        return

    # Try to figure out the instructors, class times, etc
    # For class times, suppose we find that a class occurs on day D in location L
    # from time S to E. To write this class time in the db, we need to
    # check that the class time (D, S, E, L) occurs at least 4 times.
    # We can map (D, S, E, L) to a list of dates it occurs and check count.
    instructors = []
    classtimes = []
    dsel_dates_map = {}
    potentially_biweekly = True
    for em in embeds:
        em = em.replace('\n', ' ')
        if re.search("^Primary Instructor: \w+", em):
            instructor = em.partition("Primary Instructor: ")[2]
            instructors.append(instructor)
        # Range of dates, e.g. "2022-01-05 - 2022-04-08 MWF 12:00 - 12:50 (CCIS L2-190)"
        # It's possible for there to be multiple ranges, in which case we need to create
        # classtimes for all of them.
        elif re.search("\d+-\d+-\d+ - \d+-\d+-\d+ \w+ \d+:\d+ - \d+:\d+", em):
            for curr_embed in re.findall(r"\d+-\d+-\d+ - \d+-\d+-\d+.*?\)", em):
                potentially_biweekly = False
                start_date, end_date = re.findall("\d+-\d+-\d+", curr_embed)
                days, start_t, _, end_t = re.findall("\w+ \d+:\d+ - \d+:\d+", curr_embed)[0].split(' ')
                if curr_embed.find(")") == -1:
                    curr_embed += ')'
                location = curr_embed[curr_embed.find("(") + 1: curr_embed.find(")")]
                location = location if location != "TBD" else None
                for day in days:
                    key = (day, start_t, end_t, location)
                    dates_in_range = days_in_date_range(day, start_date, end_date)
                    if key not in dsel_dates_map:
                        dsel_dates_map[key] = dates_in_range
                    else:
                        for d in dates_in_range:
                            dsel_dates_map[key].add(d)
                classtimes.append((days, start_t, end_t))
        elif re.search("\d+-\d+-\d+ \d+:\d+ - \d+:\d+", em):
            date_raw = re.findall("\d+-\d+-\d+", em)[0]
            date = datetime.strptime(date_raw, '%Y-%m-%d')
            day = "MTWHFSU"[date.weekday()]
            start_t, end_t = re.findall("\d+:\d+", em)
            location = em[em.find("(") + 1: em.find(")")]
            location = location if location != "TBD" else None
            key = (day, start_t, end_t, location)
            if key not in dsel_dates_map:
                dsel_dates_map[key] = {date}
            else:
                dsel_dates_map[key].add(date)

    instructors = str(instructors) if instructors != [] else None
    if len(dsel_dates_map) == 0:
        return
    for dsel in dsel_dates_map:
        if len(dsel_dates_map[dsel]) >= 4:
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
    fall_first = datetime.strptime("September 1, 2022", '%B %d, %Y')
    winter_first = datetime.strptime("January 5, 2023", '%B %d, %Y')
    term_start_dates["1810"] = fall_first + timedelta((0 - fall_first.weekday()) % 7)
    term_start_dates["1820"] = winter_first + timedelta((0 - winter_first.weekday()) % 7)


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
    db_cursor.execute("DELETE FROM uOfACourse WHERE course IN\
        (SELECT uOfACourse.course FROM uOfACourse LEFT JOIN uOfAClass\
        ON uOfACourse.course=uOfAClass.course AND uOfACourse.term=uOfAClass.term\
        WHERE uOfAClass.course IS NULL)")
    db_conn.commit()
    db_conn.close()
    db_path.rename(final_db_path)


db_update()
