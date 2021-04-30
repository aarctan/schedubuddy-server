import sqlite3

DATABASE = "Fall_20"

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
        if c[20] != 'O': # Enroll status must be open
            continue
        course_cmpnt = c[2]
        instructor = get_instructor_name(c[-1])
        rc_main.execute("SELECT * FROM uOfAClassTime WHERE class=?", (c[1], ))
        ct = rc_main.fetchone()
        if not cmpnts.get(course_cmpnt):
            cmpnts[course_cmpnt] = []
        if not ct: # No classtime: asynchronous class, add the class anyway
            cmpnts[course_cmpnt].append([c[2], c[3], c[5], instructor, 2147483647, -1,\
                 '', None, query, c[1]])
            continue
        t_start = get_numerical_time(ct[2])
        t_end = get_numerical_time(ct[3])
        # [Component, Section, Location, Instructor, Start_t, End_t, Days, Room, ClassId]
        cmpnts[course_cmpnt].append([c[2], c[3], c[5], instructor, t_start, t_end,\
                                    ct[4], ct[5], query, c[1]])
    return cmpnts

times = {}
rc_main.execute("SELECT * FROM uOfAClasstime")
f = rc_main.fetchall()
for c in f:
    start_t = get_numerical_time(c[2])
    end_t = get_numerical_time(c[3])
    diff = end_t-start_t
    if not diff in times.keys():
        times[diff] = 1
    else:
        times[diff] += 1
for t in times.keys():
    pass#    print(t, times[t])
#print(times)

