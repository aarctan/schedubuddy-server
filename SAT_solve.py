import sqlite3
import pycosat
from pysat.solvers import Solver, Minisat22

DATABASE = "Fall_20"

readconn_main = sqlite3.connect(DATABASE + ".db")
readconn_names = sqlite3.connect("instructor_names.db")
rc_main = readconn_main.cursor()
rc_names = readconn_names.cursor()

def get_instructor_name(uid):
    rc_names.execute("SELECT name FROM names WHERE UID=?", (uid, ))
    fetched_name = rc_names.fetchone()
    return fetched_name[0] if fetched_name else uid

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
        #instructor = get_instructor_name(c[-1])
        rc_main.execute("SELECT * FROM uOfAClassTime WHERE class=?", (c[1], ))
        ct = rc_main.fetchone()
        if not cmpnts.get(course_cmpnt):
            cmpnts[course_cmpnt] = []
        if not ct: # No classtime: asynchronous class, add the class anyway
            cmpnts[course_cmpnt].append([c[2], c[3], c[5], 2147483647, -1,\
                 '', None, query, c[1]])
            continue
        # [Component, Section, Location, #Instructor, Start_t, End_t, Days, Room, ClassId]
        cmpnts[course_cmpnt].append([c[2], c[3], c[5], ct[6], ct[7],\
                                    ct[4], ct[5], query, c[1]])
    return cmpnts

day_lookup = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}

def conflict(a,b):
    ranges = []
    for course_class in (a, b):
        start_t, end_t = course_class[3], course_class[4]
        for day in course_class[5]:
            day_mult = day_lookup[day]
            ranges.append((start_t + 2400*day_mult, end_t + 2400*day_mult))
    ranges.sort(key=lambda t: t[0])
    for i in range(len(ranges)-1):
        if ranges[i][1] > ranges[i+1][0]:
            return True
    return False

def get_classes(courses):
    classes_collection = []
    for course in courses:
        course_classes = get_course_classes(course)
        for component in course_classes.keys():
            classes_collection.append(course_classes[component])

    # Prune classes in the same collection that have the same times
    for collection in classes_collection:
        collection_times = set()
        prune_indices = []
        for i, c in enumerate(collection):
            class_times = (c[3], c[4], c[5])
            if class_times in collection_times:
                prune_indices.append(i)
            collection_times.add(class_times)
        prune_indices.reverse()
        for i in prune_indices:
            collection.pop(i)

    class_id = 1
    sat_class2id = {}
    sat_id2class = {}
    for component in classes_collection:
        for course_class in component:
            sat_class2id[course_class[-1]] = class_id
            sat_id2class[class_id] = course_class[-1]
            class_id += 1

    clauses = []
    for collection in classes_collection:
        # Singleton component: must be in schedule
        if len(collection) == 1:
            clauses.append([sat_class2id[collection[0][-1]]])
            continue
        # Cannot ever have two classes from the same component
        for i in range(len(collection)):
            for j in range(i+1, len(collection)):
                clauses.append([-1 * sat_class2id[collection[i][-1]],\
                                -1 * sat_class2id[collection[j][-1]]])

    for collection in classes_collection:
        collection_clause = []
        for course_class in collection:
            collection_clause.append(sat_class2id[course_class[-1]])
        clauses.append(collection_clause)

    for i in range(len(classes_collection)):
        collection_i = classes_collection[i]
        for j in range(i+1, len(classes_collection)):
            collection_j = classes_collection[j]
            for k in range(len(classes_collection[i])):
                for l in range(len(classes_collection[j])):
                    class_a = collection_i[k]
                    class_b = collection_j[l]
                    if conflict(class_a, class_b):
                        clauses.append([-1 * sat_class2id[class_a[-1]],\
                            -1 * sat_class2id[class_b[-1]]])
    
    sols = []
    for sol in pycosat.itersolve(clauses):
        new_sol = [i for i in sol if i > 0]
        sols.append(new_sol)
    print(len(sols))

    sol = sols[0]
    for class_sat in sol:
        class_id = sat_id2class[class_sat]
        rc_main.execute("SELECT * FROM uOfAClass WHERE class=?", (class_id,))
        course_class = rc_main.fetchone()
        #print(course_class[-6])

get_classes(["CHEM 101", "CHEM 261", "BIOL 107"])
