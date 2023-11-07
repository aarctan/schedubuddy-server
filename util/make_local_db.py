import random
import re, sqlite3, json, time
import string
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path

term_start_dates = {}
year_str = str(datetime.now().year)


def days_in_date_range(day, range_start, range_end):
    # Returns a list of dates that a 'day', e.g. 'M', occurs in the range of dates
    enum_weekday = {"M": 0, "T": 1, "W": 2, "H": 3, "R": 3, "F": 4, "S": 5, "U": 6}
    weekday = enum_weekday[day]
    d_s = datetime.strptime(range_start, "%Y-%m-%d")
    d_e = datetime.strptime(range_end, "%Y-%m-%d")
    dates = []
    for d_ord in range(d_s.toordinal(), d_e.toordinal() + 1):
        d = datetime.fromordinal(d_ord)
        if d.weekday() == weekday:
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
    subject = raw_class_obj["subject"].replace("_", " ")
    catalog = raw_class_obj["catalog"]
    courseId = f"{subject} {catalog}"
    classId = raw_class_obj["classId"]
    component = raw_class_obj["component"][:3]
    section = raw_class_obj["section"]
    classTimes = raw_class_obj["classTimes"]
    instructor = raw_class_obj["instructor"]
    instructionMode = "In Person"

    # Exit if this class has no times. We ignore asynchronous classes, or classes currently not offered.
    if len(classTimes) == 0:
        return

    # Exit if this class has already been written
    db_cursor.execute(
        "SELECT * FROM uOfAClass WHERE term=? AND course=? AND class=?",
        (termId, courseId, classId),
    )
    if db_cursor.fetchone():
        return

    # Try to figure out the instructors, class times, etc
    # For class times, suppose we find that a class occurs on day D in location L
    # from time S to E. To write this class time in the db, we need to
    # check that the class time (D, S, E, L) occurs at least 4 times.
    # We can map (D, S, E, L) to a list of dates it occurs and check count.
    # 7/11/2023: exempt DSEL>=4 check if D is on the weekend.
    dsel_dates_map = {}
    potentially_biweekly = True
    date_pattern = r"\d{4}-\d{2}-\d{2}"  # e.g. 2024-01-08

    for classtime in classTimes:
        dates, times, loc = classtime[0], classtime[1], classtime[2]
        if not "-" in times:
            continue
        start_t_str, end_t_str = times.split(" - ")
        start_t = time.strftime("%I:%M %p", time.strptime(start_t_str, "%H:%M"))
        end_t = time.strftime("%I:%M %p", time.strptime(end_t_str, "%H:%M"))
        if "(" in dates:  # date range, e.g. "2024-01-08 - 2024-02-01 (MWF)"
            days = re.search(r"\((\w+)\)", dates)  # days = MWF
            days = days.group(0)[1:-1]
            dates = re.findall(date_pattern, dates)
            start_date, end_date = dates[0], dates[1]
            for day in days:
                key = (day, start_t, end_t, loc)
                dsel_dates_map.setdefault(key, set()).update(days_in_date_range(day, start_date, end_date))
        else:  # single date, e.g. "2023-09-20"
            date = re.findall(date_pattern, dates)[0]
            class_date = datetime.strptime(date, "%Y-%m-%d")
            day = "MTWHFSU"[class_date.weekday()]
            key = (day, start_t, end_t, loc)
            dsel_dates_map.setdefault(key, set()).add(class_date)

    instructors = "['" + instructor + "']" if instructor else None

    # only write courses we know the schedules for
    # Write the term if it does not exist
    db_cursor.execute(
        "INSERT OR IGNORE INTO uOfATerm VALUES (?, ?, ?, ?)",
        (termId, termName, None, None),
    )

    # Write a new course for the term if it does not exist
    db_cursor.execute("SELECT * FROM uOfACourse WHERE term=? AND course=?", (termId, courseId))
    if not db_cursor.fetchone():
        db_cursor.execute(
            "INSERT INTO uOfACourse VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                termId,
                courseId,
                subject,
                catalog,
                courseId,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )

    for dsel in dsel_dates_map:
        ece_errata = (
            subject == "ECE" and catalog in ("202", "210") and component == "LAB"
        )  # errata reported in issue 26
        if len(dsel_dates_map[dsel]) >= 4 or dsel[0] in ("S", "U") or ece_errata:
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
                    if ece_errata:  # this may apply to non ECE cases as well in case labs start on the first week
                        biweekly = 1 if (datetimes[0] - term_start_dates[str(termId)]).days < 0 else 2
            # biweekly = None # temporarily disable biweekly classes
            day, start_t, end_t, location = dsel
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
    db_cursor.execute(
        f"CREATE TABLE uOfATerm(term TEXT UNIQUE, termTitle TEXT,\
    startDate TEXT, endDate TEXT)"
    )
    db_cursor.execute(
        f"CREATE TABLE uOfACourse(term TEXT, course TEXT,\
    subject TEXT, course_num TEXT, asString TEXT, units TEXT, courseTitle TEXT,\
    subjectTitle TEXT, courseDescription TEXT, career TEXT, faculty TEXT,\
    facultyCode TEXT, department TEXT, departmentCode TEXT)"
    )
    db_cursor.execute(
        f"CREATE TABLE uOfAClass(term TEXT, course TEXT,\
    class TEXT, component TEXT, section TEXT, asString TEXT, instructorUid TEXT,\
    campus TEXT, location TEXT, capacity TEXT, classStatus TEXT, classNotes TEXT,\
    classType TEXT, consent TEXT, startDate TEXT, endDate TEXT, enrollStatus TEXT,\
    gradingBasis TEXT, examStatus TEXT, examDate TEXT, examStartTime TEXT,\
    examEndTime TEXT, autoEnroll TEXT, instructionMode TEXT, session TEXT, units TEXT)"
    )
    db_cursor.execute(
        f"CREATE TABLE uOfAClassTime(term TEXT, course TEXT,\
    class TEXT, location TEXT, startDate TEXT, endDate TEXT, day TEXT, startTime TEXT,\
    endTime TEXT, biweekly TEXT)"
    )
    db_cursor.execute(f"CREATE TABLE meta(lastUpdated FLOAT)")


def retrieve_term_start_dates():
    # Assume that (biweekly) labs do not occur on the first week. Therefore, they
    # must start on the monday after the first week. All labs during this week
    # are assumed to have a biweekly flag of 1, and ones that start the week
    # after the first week of labs will have a biweekly flag of 2.

    # first day of fall in course_num:
    # "Fall Term and Fall/Winter two-term classes begin. Exceptions may apply; students must consult with their Faculty office."
    # first day of winter in course_num:
    # "Winter Term classes begin. Exceptions may apply; students must consult with their Faculty office."
    fall_first = datetime.strptime("September 5, 2023", "%B %d, %Y")
    winter_first = datetime.strptime("January 8, 2024", "%B %d, %Y")
    term_start_dates["1850"] = fall_first + timedelta((0 - fall_first.weekday()) % 7)
    term_start_dates["1860"] = winter_first + timedelta((0 - winter_first.weekday()) % 7)


def prune_db(db_cursor):
    db_cursor.execute(
        f"DELETE FROM uOfAClass WHERE class IN (SELECT c.class FROM uOfAClass c LEFT JOIN uOfAClassTime ct\
                       ON c.class = ct.class WHERE ct.class IS NULL)"
    )
    db_cursor.execute(
        f"DELETE FROM uOfACourse WHERE course IN (SELECT c.course FROM uOfACourse c LEFT JOIN uOfAClass cl\
                       ON c.course = cl.course WHERE cl.course IS NULL)"
    )


def update_last_updated(db_cursor, last_updated: float) -> None:
    db_cursor.execute("INSERT INTO meta VALUES (?)", (last_updated,))


def db_update():
    dirname = Path(__file__).parent
    default_db_path = dirname / "../local/cataloguedb.db"
    default_raw_path = dirname / "../local/raw.json"

    parser = ArgumentParser()
    parser.add_argument(
        "--db",
        "-d",
        help="database path. overwrites if it exists already",
        default=default_db_path,
    )
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

    courses = data["courses"]
    db_conn = sqlite3.connect(db_path)
    db_cursor = db_conn.cursor()
    initialize_db(db_cursor)
    update_last_updated(db_cursor, data["last_updated"])
    retrieve_term_start_dates()
    for raw_class_obj in courses:
        process_and_write(raw_class_obj, db_cursor)
    prune_db(db_cursor)

    db_conn.commit()
    db_conn.close()
    db_path.rename(final_db_path)


db_update()
