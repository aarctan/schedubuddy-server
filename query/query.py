import os, sqlite3, json, sys, logging
from collections import defaultdict

def str_t_to_int(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

class QueryExecutor:
    def __init__(self):
        dirname = os.path.dirname(__file__)
        db_path = os.path.join(dirname, "../local/cataloguedb.db")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        uni_format_path = os.path.join(dirname, "../formats/uAlberta.json")
        university_json_f = open(uni_format_path)
        self._uni_json = json.load(university_json_f)
        self._minimal_class_keys = ['asString', 'class', 'component', 'course',\
            'InstructionMode', 'instructorName', 'instructorUid', 'location',\
            'section', 'term']
        university_json_f.close()
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        self._term_class_cache = {}
        for term_obj in self.get_terms()["objects"]:
            self._term_class_cache[str(term_obj["term"])] = {}
    
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
        course_query = f"SELECT course, asString FROM uOfACourse WHERE term=?"
        self._cursor.execute(course_query, (str(term),))
        course_rows = self._cursor.fetchall()
        json_res = []
        for course_row in course_rows:
            json_course = {"course": course_row[0], "asString": course_row[1]}
            json_res.append(json_course)
        return {"objects":json_res}
    
    def get_term_rooms(self, term:int):
        course_query = f"SELECT DISTINCT location FROM uOfAClassTime WHERE term=?"
        self._cursor.execute(course_query, (str(term),))
        location_rows = self._cursor.fetchall()
        json_res = []
        for location_row in location_rows:
            if not location_row[0]:
                continue
            json_room = {"location": location_row[0]}
            json_res.append(json_room)
        return {"objects":json_res}

    def _coalesce_identical_classtimes(self, classtimes):
        res = []
        i = 0
        while i < len(classtimes):
            a = classtimes[i]
            j = i+1
            while j < len(classtimes):
                b = classtimes[j]
                if a["startTime"] == b["startTime"] and a["day"] == b["day"]:
                    if a["location"] and b["location"]:
                        if a["location"] != b["location"]:
                            a["location"] = f'{a["location"]}, {b["location"]}'
                    else:
                        a["location"] = a["location"] if a["location"] else b["location"]
                    del classtimes[j]
                    j -= 1
                j += 1
            res.append(a)
            i += 1
        return res

    def _get_classtimes(self, term:int,c_class:str):
        classtime_query = f"SELECT * FROM uOfAClassTime WHERE term=? AND class=?"
        self._cursor.execute(classtime_query, (str(term), c_class))
        classtime_rows = self._cursor.fetchall()
        keys = self._uni_json["calendar"]["uOfAClassTime"]
        json_res = []
        for classtime_row in classtime_rows:
            json_classtime = {}
            for k, attr in enumerate(classtime_row[:-1]):
                key = keys[k]
                if key not in ("term", "course", "class"):
                    json_classtime[key] = attr
            json_classtime["biweekly"] = classtime_row[-1] if classtime_row[-1] else 0
            json_res.append(json_classtime)
        self._coalesce_identical_classtimes(json_res)
        return json_res
    
    # Need to check if the preferences still allow of the generation of schedules
    # containing a class from each possible component (e.g. LEC, SEM).
    def filter_check(self, term:int, course:str, filtered_rows):
        class_query = "SELECT * FROM uOfAClass WHERE term=? AND course=?"
        self._cursor.execute(class_query, (str(term), course))
        all_class_rows = self._cursor.fetchall()
        possible_components = set()
        filtered_components = set()
        for class_row in all_class_rows:
            possible_components.add(class_row[3])
        for class_row in filtered_rows:
            filtered_components.add(class_row[3])
        return len(possible_components) == len(filtered_components)
        
    def get_course_classes(self, term:int, course:str, prefs):
        class_query = "SELECT * FROM uOfAClass WHERE term=? AND course=?"
        if prefs["ONLINE_CLASSES"] == False:
            class_query += " AND instructionMode!=? AND instructionMode!=?"
            self._cursor.execute(class_query, (str(term), course, "Remote Delivery", "Internet"))
        else:
            self._cursor.execute(class_query, (str(term), course))
        class_rows = self._cursor.fetchall()
        valid_filters = self.filter_check(term, course, class_rows)
        if not valid_filters:
            return None
        json_res = []
        all_classes_evening_and_filter = True
        for class_row in class_rows:
            json_class = {}
            for k, attr in enumerate(class_row):
                key = self._uni_json["calendar"]["uOfAClass"][k]
                json_class[key] = attr
            json_class["classtimes"] = self._get_classtimes(term, json_class["class"])
            if prefs["EVENING_CLASSES"] == False and json_class["component"] == "LEC":
                has_evening_class = False
                for classtime in json_class["classtimes"]:
                    start_t = str_t_to_int(classtime["startTime"])
                    end_t = str_t_to_int(classtime["endTime"])
                    if 170 <= (end_t - start_t) <= 180:
                        has_evening_class = True
                    else:
                        all_classes_evening_and_filter = False
                if has_evening_class:
                    continue
            json_res.append(json_class)
        if prefs["EVENING_CLASSES"] == False and all_classes_evening_and_filter:
            return None
        return {"objects":json_res}
    
    def _get_class_obj(self, term:int, class_id:str, loc_filter=None, minimal=False):
        if class_id in self._term_class_cache[str(term)]:
            return self._term_class_cache[str(term)][class_id]
        class_query = f"SELECT * FROM uOfAClass WHERE term=? AND class=?"
        self._cursor.execute(class_query, (str(term), class_id))
        class_row = self._cursor.fetchone()
        json_res = {}
        for k, attr in enumerate(class_row):
            key = self._uni_json["calendar"]["uOfAClass"][k]
            if minimal and not key in self._minimal_class_keys:
                continue
            json_res[key] = attr
        json_res["classtimes"] = []
        classtimes = self._get_classtimes(term, class_id)
        if loc_filter:
            for classtime in classtimes:
                if classtime["location"] == loc_filter:
                    json_res["classtimes"].append(classtime)
        else:
            json_res["classtimes"] = classtimes
        json_res["instructorName"] = json_res["instructorUid"]
        ret_obj = {"objects":json_res}
        self._term_class_cache[str(term)][class_id] = ret_obj
        return ret_obj
    
    def get_course_name(self, term, course_id):
        course_query = "SELECT asString from uOfACourse where term=? AND course=?"
        self._cursor.execute(course_query, (str(term), str(course_id)))
        course_name = self._cursor.fetchone()
        return course_name[0]
    
    def get_schedules(self, term:int, course_id_list:str, prefs, gen_sched):
        course_id_list = [str(c) for c in course_id_list[1:-1].split(',')]
        prefs_list = prefs if type(prefs) == list else [str(p) for p in prefs[1:-1].split(',')]
        start_time_pref = prefs_list[2]
        if len(start_time_pref) == 7: # no trailing 0
            start_time_pref = '0' + start_time_pref
        prefs = {
            "EVENING_CLASSES": True if int(prefs_list[0]) == 1 else False,
            "ONLINE_CLASSES": True if int(prefs_list[1]) == 1 else False,
            "IDEAL_START_TIME": str_t_to_int(start_time_pref)/60,
            "IDEAL_CONSECUTIVE_LENGTH": int(prefs_list[3]),
            "LIMIT": int(prefs_list[4])
        }
        classes = []
        for course_id in course_id_list:
            course_classes = self.get_course_classes(term, course_id, prefs)
            if not course_classes:
                return {"objects": {"schedules":[], "aliases": [],
                    "errmsg": f"No schedules to display: the provided settings\
                    filtered out all classes for " + self.get_course_name(term, course_id)}}
            classes.append(course_classes)

        c_list = []
        for course_id in course_id_list:
            try:
                c_list.append(self.get_course_name(term, course_id))
            except:
                pass
        logging.debug(c_list)

        sched_obj = gen_sched.generate_schedules({"objects":classes}, prefs)
        if "errmsg" in sched_obj:
            return {"objects":sched_obj}
        schedules = sched_obj["schedules"]
        json_res = {}
        json_schedules = []
        for schedule in schedules:
            json_sched = []
            for class_id in schedule:
                class_obj = self._get_class_obj(term, class_id, minimal=True)
                json_sched.append(class_obj)
            json_schedules.append(json_sched)
        json_res["schedules"] = json_schedules
        json_res["aliases"] = sched_obj["aliases"]
        return {"objects":json_res}
    
    def get_room_classes(self, term, room):
        print(f"Room '{room}' lookup in term {term}")
        query = "SELECT class FROM uOfAClassTime WHERE term=? AND location=?"
        self._cursor.execute(query, (str(term), str(room)))
        classes = self._cursor.fetchall()
        json_res = {}
        json_sched = []
        for class_id in classes:
            json_sched.append(self._get_class_obj(term, class_id[0], room))
        json_res["schedules"] = [json_sched]
        json_res["aliases"] = {}
        return {"objects": json_res}

    def get_avaliable_rooms(self, term, weekday, starttime, endtime):

        # Get all distinct rooms
        course_query = f"SELECT DISTINCT location FROM uOfAClassTime WHERE term=?"
        self._cursor.execute(course_query, (str(term),))
        all_rooms = set(map(lambda x: x[0], self._cursor.fetchall())) 
        
        # Loop over all all avaliable
        all_classes_today_query = f"SELECT * FROM uOfAClassTime WHERE term=? AND day=?"
        self._cursor.execute(all_classes_today_query, (str(term), weekday))
        all_classes_today = self._cursor.fetchall()

        self._remove_conflicting_classes(all_rooms, all_classes_today, starttime, endtime)
        return self._get_nested_dict_from_location(all_rooms)

    def _get_nested_dict_from_location(self, rooms):
        organized_dict = defaultdict(list)
        for room in rooms:
            areaName = room.split()[0]
            organized_dict[areaName].append(room)
        return organized_dict

    def _remove_conflicting_classes(self, all_rooms, all_classes, starttime, endtime):

        starttime_as_min_int = str_t_to_int(starttime)
        endtime_as_min_int = str_t_to_int(endtime)

        all_rooms.discard("Location TBD")

        # Test each class for interesction
        for classObj in all_classes:
            classLoc = classObj[3]
            classStart = str_t_to_int(classObj[7])
            classEnd = str_t_to_int(classObj[8])
            # If not in the set, don't do any computation
            if classLoc not in all_rooms: continue
            # else, if overlap, then remove from avaliable classes
            elif starttime_as_min_int <= classEnd and classStart <= endtime_as_min_int: all_rooms.discard(classLoc)

        return
