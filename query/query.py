import sqlite3
import os
import json

class QueryExecutor:
    def __init__(self):
        dirname = os.path.dirname(__file__)
        db_path = os.path.join(dirname, "../local/database.db")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        uni_format_path = os.path.join(dirname, "../formats/uAlberta.json")
        university_json_f = open(uni_format_path)
        self._uni_json = json.load(university_json_f)
        university_json_f.close()
    
    def get_terms(self) -> list:
        query = f"SELECT * FROM uOfATerm"
        self._cursor.execute(query)
        terms = self._cursor.fetchall()
        json_res = []
        for term in terms:
            json_term = {}
            for k, attr in enumerate(term):
                json_term[self._uni_json["calendar"]["uOfATerm"][k]] = attr
            json_res.append(json_term)
        return {"objects":json_res}

qe = QueryExecutor()
#print(qe.get_terms())




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


