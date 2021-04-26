DATABASE = "Fall_20"

import sqlite3
readconn_main = sqlite3.connect(DATABASE+".db")
readconn_names = sqlite3.connect("instructor_names.db")
rc_main = readconn_main.cursor()
rc_names = readconn_names.cursor()

def get_instructor_name(uid):
    rc_names.execute("SELECT name FROM names WHERE UID=?", (uid, ))
    fetched_name = rc_names.fetchone()
    return fetched_name[0] if fetched_name else None

def get_numerical_time(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

while True:
    query = input("Enter course (e.g. \"chem 101\"): ").upper()
    rc_main.execute("SELECT course FROM uOfACourse WHERE asString=?",\
                    (query,))
    courseID = rc_main.fetchone()
    if not courseID:
        print("No offering for " + query + " found.")
        continue
    courseID = courseID[0]
    rc_main.execute("SELECT * FROM uOfAClass WHERE course=?", (courseID,))
    classes = rc_main.fetchall()
    cmpnts = {}
    for c in classes:
        classID = c[1]
        rc_main.execute("SELECT * FROM uOfAClassTime WHERE class=?",\
                        (classID, ))
        ct = rc_main.fetchone()
        if not ct:
            continue
        component = c[2]
        if not cmpnts.get(component):
            cmpnts[component] = []
        instructor = get_instructor_name(c[-1])
        t_start = get_numerical_time(ct[2])
        t_end = get_numerical_time(ct[3])
        cmpnts[component].append([c[3], c[5], instructor, ct[2], ct[3],\
                                  ct[4], ct[5]])
    for cmpt in cmpnts:
        print(cmpt)
        for x in cmpnts[cmpt]:
            print(x)
        
    
