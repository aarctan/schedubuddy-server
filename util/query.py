import sqlite3

DATABASE = "Fall_20"

readconn_main = sqlite3.connect(DATABASE + ".db")
readconn_names = sqlite3.connect("instructor_names.db")
rc_main = readconn_main.cursor()
rc_names = readconn_names.cursor()

def get_instructor_name(uid):
    rc_names.execute("SELECT name FROM names WHERE UID=?", (uid, ))
    fetched_name = rc_names.fetchone()
    return fetched_name[0] if fetched_name else "Unknown Prof"

def get_numerical_time(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

def get_course_classes(query):
    query = query.upper()
    rc_main.execute("SELECT course FROM uOfACourse WHERE asString=?", (query,))
    courseID = rc_main.fetchone()
    if not courseID:
        print("No offering for " + query + " found.")
        return
    courseID = courseID[0]
    rc_main.execute("SELECT * FROM uOfAClass WHERE course=?", (courseID,))
    classes = rc_main.fetchall()
    cmpnts = {}
    for c in classes:
        rc_main.execute("SELECT * FROM uOfAClassTime WHERE class=?", (c[1], ))
        ct = rc_main.fetchone()
        if not ct:
            continue
        course_cmpnt = c[2]
        if not cmpnts.get(course_cmpnt):
            cmpnts[course_cmpnt] = []
        instructor = get_instructor_name(c[-1])
        t_start = get_numerical_time(ct[2])
        t_end = get_numerical_time(ct[3])
        # [Section, Location, Instructor, Start_t, End_t, Days, Room]
        cmpnts[course_cmpnt].append([c[3], c[5], instructor, t_start, t_end,\
                                    ct[4], ct[5]])
    for cmpnt in cmpnts:
        print(cmpnt)
        for entry in cmpnts[cmpnt]:
            print(entry)

get_course_classes("math 214")