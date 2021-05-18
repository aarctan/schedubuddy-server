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
    
    def get_terms(self):
        term_query = f"SELECT * FROM uOfATerm"
        self._cursor.execute(term_query)
        terms = self._cursor.fetchall()
        json_res = []
        for term in terms:
            json_term = {}
            for k, attr in enumerate(term):
                json_term[self._uni_json["calendar"]["uOfATerm"][k]] = attr
            json_res.append(json_term)
        return {"objects":json_res}
    
    def get_term_courses(self, term:int):
        course_query = f"SELECT * FROM uOfACourse WHERE term=?"
        self._cursor.execute(course_query, (str(term),))
        course_rows = self._cursor.fetchall()
        json_res = []
        for course_row in course_rows:
            json_course = {}
            for k, attr in enumerate(course_row):
                json_course[self._uni_json["calendar"]["uOfACourse"][k]] = attr
            json_res.append(json_course)
        return {"objects":json_res}
    
    def _get_classtimes(self, term:int,c_class:str):
        classtime_query = f"SELECT * FROM uOfAClassTime WHERE term=? AND class=?"
        self._cursor.execute(classtime_query, (str(term), c_class))
        classtime_rows = self._cursor.fetchall()
        json_res = []
        for classtime_row in classtime_rows:
            json_classtime = {}
            for k, attr in enumerate(classtime_row):
                key = self._uni_json["calendar"]["uOfAClassTime"][k]
                if key not in ("term", "course", "class"):
                    json_classtime[key] = attr
            json_res.append(json_classtime)
        return json_res
    
    def get_department_courses(self, term:int, department:str):
        department_query = f"SELECT * FROM uOfACourse WHERE term=? AND departmentCode=?"
        self._cursor.execute(department_query, (str(term), department))
        course_rows = self._cursor.fetchall()
        json_res = []
        for course_row in course_rows:
            json_course = {}
            for k, attr in enumerate(course_row):
                json_course[self._uni_json["calendar"]["uOfACourse"][k]] = attr
            json_res.append(json_course)
        return {"objects":json_res}

    def get_course_classes(self, term:int, course:str):
        class_query = f"SELECT * FROM uOfAClass WHERE term=? AND course=?"
        self._cursor.execute(class_query, (str(term), course))
        class_rows = self._cursor.fetchall()
        json_res = []
        for class_row in class_rows:
            json_class = {}
            for k, attr in enumerate(class_row):
                key = self._uni_json["calendar"]["uOfAClass"][k]
                json_class[key] = attr
            json_class["classtimes"] = self._get_classtimes(term, json_class["class"])
            json_res.append(json_class)
        return {"objects":json_res}
    
    def _get_class_obj(self, term:int, class_id:str):
        class_query = f"SELECT * FROM uOfAClass WHERE term=? AND class=?"
        self._cursor.execute(class_query, (str(term), class_id))
        class_row = self._cursor.fetchone()
        json_res = {}
        for k, attr in enumerate(class_row):
            key = self._uni_json["calendar"]["uOfAClass"][k]
            json_res[key] = attr
        json_res["classtimes"] = self._get_classtimes(term, class_id)
        return {"objects":json_res}
    
    def get_schedules(self, term:int, course_id_list:str, gen_sched_fp):
        # course_id_list is of form: "[######,######,...,######]"
        course_id_list = [str(c) for c in course_id_list[1:-1].split(',')]
        classes = []
        for course_id in course_id_list:
            course_classes = self.get_course_classes(term, course_id)
            classes.append(course_classes)
        sched_alias = gen_sched_fp({"objects":classes})
        schedules = sched_alias["schedules"]
        json_res = {}
        json_schedules = []
        for schedule in schedules:
            json_sched = []
            for class_id in schedule:
                json_sched.append(self._get_class_obj(term, class_id))
            json_schedules.append(json_sched)
        json_res["schedules"] = json_schedules
        json_res["aliases"] = sched_alias["aliases"]
        return {"objects":json_res}

    

#print(qe.get_course_classes(1770, "000001"))



'''
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
'''

