import sqlite3

DATABASE = "Fall_21"

readconn_main = sqlite3.connect(DATABASE + ".db")
readconn_names = sqlite3.connect("instructor_names.db")
rc_main = readconn_main.cursor()
rc_names = readconn_names.cursor()

def get_instructor_name(uid):
    rc_names.execute("SELECT name FROM names WHERE UID=?", (uid, ))
    fetched_name = rc_names.fetchone()
    return fetched_name[0] if fetched_name else uid

def get_numerical_time(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

def get_course_classes(query, no_online=True):
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
        if c[20] != 'O': # Enroll status must be open
            continue
        if no_online and c[5] == "ONLINE":
            continue
        course_cmpnt = c[2]
        instructor = get_instructor_name(c[-1])
        rc_main.execute("SELECT * FROM uOfAClassTime WHERE class=?", (c[1], ))
        cts = rc_main.fetchall()
        if not cmpnts.get(course_cmpnt):
            cmpnts[course_cmpnt] = []
        if not cts: # No classtime: asynchronous class, add the class anyway
            #cmpnts[course_cmpnt].append([c[2], c[3], c[5], instructor, 2147483647, -1,\
            #     '', None, query, c[1]])
            continue
        class_times = []
        for ct in cts:
            t_start = get_numerical_time(ct[2])
            t_end = get_numerical_time(ct[3])
            class_times.append((t_start, t_end, ct[4], ct[5]))
            # [Component, Section, Location, Instructor, Start_t, End_t, Days, Room, ClassId]
        cmpnts[course_cmpnt].append([c[2], c[3], c[5], instructor, class_times, query, c[1]])
    return cmpnts

#print(get_course_classes("MATH 117"))

def get_conflicts_set():
    rc_main.execute("SELECT * FROM classTimeConflicts")
    conflicts = rc_main.fetchall()
    conflict_set = set()
    for conflict in conflicts:
        a_id = conflict[0]
        a_conflicts = conflict[1][1:-1].replace("'", '').split(', ')
        for a_conflict in a_conflicts:
            conflict_set.add((a_id, a_conflict))
    return conflict_set


