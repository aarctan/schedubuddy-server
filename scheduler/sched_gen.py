from random import shuffle
from . import MRV
import ctypes, heapq

ASSUMED_COMMUTE_TIME = 30

def str_t_to_int(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

day_mapping = {
            'M': 0,
            'T': 1,
            'W': 2,
            'H': 3,
            'F': 4,
            'S': 5,
            'U': 6
}
    
class Block(ctypes.Structure):
    _fields_ = [("Day", ctypes.c_int),
                ("Start", ctypes.c_int),
                ("End", ctypes.c_int)]
    
so_f = r"C:\Users\muham\Documents\schedubuddy-server\util\evaluate.so"
functions = ctypes.CDLL(so_f)
functions.evaluate.argtypes = [ctypes.POINTER(Block), ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int]
functions.evaluate.restype = ctypes.c_float

class ValidSchedule:
    def __init__(self, schedule, aliases, blocks, num_pages, prefs):
        self._schedule = schedule
        self._aliases = aliases
        self._num_pages = num_pages
        self._prefs = prefs
        sched_blocks = (Block * len(blocks))()
        for i, s in enumerate(blocks):
            sched_blocks[i] = Block(*s)
        self.score = functions.evaluate(sched_blocks, len(blocks), int(prefs["IDEAL_CONSECUTIVE_LENGTH"]) * 60, int(prefs["IDEAL_START_TIME"]) * 60, 30)

class ScheduleFactory:
    def __init__(self, exhaust_threshold=500000):
        self._day_index = {'M':0, 'T':1, 'W':2, 'H':3, 'F':4, 'S':5, 'U':6}
        self._CONFLICTS = set()
        self._component_blocks = {}

    def _conflicts(self, class_a, class_b):
        class_a_id, class_b_id = class_a[0], class_b[0]
        if (class_a_id, class_b_id) in self._CONFLICTS:
            return True
        ranges = []
        for course_class in (class_a, class_b):
            classtimes = course_class[5]
            ct_ranges = []
            for classtime in classtimes:
                start_t, end_t = classtime[1], classtime[2]
                for day in classtime[0]:
                    day_mult = self._day_index[day]
                    ct_range = (start_t + 2400*day_mult, end_t + 2400*day_mult, classtime[4])
                    # 7/11/2023: consider a classtime that is an entire superset of the same classtime but in
                    # a different location. for example, C1 = 9am-5pm in E1-003 and 12pm-5pm in E1-013.
                    # we should detect this case as a non-conflict (there is a real instance of this).
                    if len(ct_ranges) > 0:
                        is_subset = False
                        for (existing_range, compare_day) in ct_ranges:
                            if day == compare_day and ct_range[0] >= existing_range[0] and ct_range[1] <= existing_range[1]:
                                is_subset = True
                        if not is_subset:
                            ct_ranges.append((ct_range, day))
                    else:
                        ct_ranges.append((ct_range, day))
            for (ct_range, _) in ct_ranges:
                ranges.append(ct_range)
        ranges.sort(key=lambda t: t[0])
        for i in range(len(ranges)-1):
            if ranges[i][1] > ranges[i+1][0]:
                biweekly1, biweekly2 = int(ranges[i][2]), int(ranges[i+1][2])
                if biweekly1 == 0 or biweekly2 == 0 or (biweekly1 == biweekly2):
                    self._CONFLICTS.add((class_a_id, class_b_id))
                    self._CONFLICTS.add((class_b_id, class_a_id))
                    return True
        return False

    def _json_sched(self, sched):
        return [c[0] for c in sched]

    # Given a list of components, returns the size of the cross product. This is
    # useful for knowing the workload prior to computing it, which can be grow
    # more than exponentially fast.
    def _cross_prod_cardinality(self, components):
        cardinality = 1
        for component in components:
            cardinality *= len(component)
        return cardinality

    def _master_sort(self, schedules, prefs):
        sched_objs = []
        num_pages = len(schedules)
        for schedule in schedules:
            blocks = [item[:3] for sublist in schedule for item in sublist[5]]
            blocks = [(day_mapping[t[0]], t[1], t[2]) for t in blocks]
            sched_obj = ValidSchedule(schedule, [], blocks, num_pages, prefs)
            sched_objs.append(sched_obj)
        overall_sorted = sorted(sched_objs, key=lambda SO: SO.score, reverse=True)
        overall_sorted = overall_sorted[:min(prefs["LIMIT"], num_pages)]
        return overall_sorted
    
    # param course_list is a list of strings of form "SUBJ CATALOG" e.g. "CHEM 101".
    # returns a tuple (components, aliases). components is list of components where
    #   a component is all classes belonging to a particular component of a course.
    #   e.g. create_components(["CHEM 101"]) will find components for LEC, SEM, LAB,
    #   and CSA. aliases maps string class IDs to all classes of the same component
    #   that share identical start times, end times, and days, used to reduce the
    #   search space to only unique "looking" schedules.
    def _create_components(self, courses_dict):
        components = []
        aliases = {}
        for course_dict in courses_dict:
            for component in course_dict.keys():
                component_classes = course_dict[component]
                new_component = []
                component_aliases = {}
                classtime_to_first_class = {}
                for component_class in component_classes:
                    class_comp_str = component_class[1] + ' ' + component_class[2] # e.g., LEC A1
                    class_times = []
                    for i in range(len(component_class[5])):
                        ct_i = component_class[5][i]
                        class_times.append((ct_i[0], ct_i[1], ct_i[2], ct_i[4]))
                    class_times = tuple(class_times)
                    if class_times in classtime_to_first_class:
                        first_class = classtime_to_first_class[class_times]
                        alias_info = [component_class[0], class_comp_str]
                        component_aliases[first_class].append(alias_info)
                        aliases[first_class] = component_aliases[first_class]
                    else:
                        first_class_key = component_class[0]
                        classtime_to_first_class[class_times] = first_class_key
                        component_aliases[first_class_key] = []
                        new_component.append(component_class)
                components.append(new_component)
        return (components, aliases)

    def _create_course_dict(self, courses_obj):
        attr_tuples = ("class", "component", "section", "campus", "instructorUid")
        courses = []
        for course_obj in courses_obj["objects"]:
            course = {}
            class_obj = course_obj["objects"]
            for course_class in class_obj:
                component = course_class["component"]
                class_dict = [course_class[attr] for attr in attr_tuples]
                times = []
                for i in range(len(course_class["classtimes"])):
                    ct = course_class["classtimes"][i]
                    times.append((ct["day"],
                        str_t_to_int(ct["startTime"]), str_t_to_int(ct["endTime"]),
                        course_class["location"], ct["biweekly"]))
                class_dict.append(times)
                if component in course:
                    course[component].append(class_dict)
                else:
                    course[component] = [class_dict]
            courses.append(course)
        return courses

    def _build_conflicts_set(self, components):
        flat_classes = [e for c in components for e in c]
        for class_a in flat_classes:
            for class_b in flat_classes:
                _ = self._conflicts(class_a, class_b)

    # Generate valid schedules for a string list of courses. First construct a
    # a list of components, where a "component" is a set of classes where each
    # class contains information such as class time, id, location, etc, and share
    # a component if they have the same course id and component such as LEC or
    # LAB. Early exit if the SAT solver proves unsatisfiability. If the size of
    # possibly valid schedules is within a computational threshold T, then
    # attempt to validate all schedules. If the size exceeds the threshold,
    # randomly sample from every axis (component) and gather a subset of all
    # possibly valid schedules of size T.
    def generate_schedules(self, courses_obj, prefs):
        course_conflicts = []
        for i in range(0, len(courses_obj['objects'])):
            for j in range(i+1, len(courses_obj['objects'])):
                c1, c2 = courses_obj['objects'][i], courses_obj['objects'][j]
                obj = {'objects': [c1, c2]}
                courses_dict = self._create_course_dict(obj)
                components, _ = self._create_components(courses_dict)
                self._build_conflicts_set(components)
                mrv_model = MRV.MRV_Model(components, self._CONFLICTS)
                mrv_model.solve()
                if len(mrv_model.get_valid_schedules()) == 0:
                    course_conflicts.append(f"{c1['objects'][0]['course']} conflicts with {c2['objects'][0]['course']}")
        if len(course_conflicts) > 0:
            return {"schedules":[], "aliases":[],
                "errmsg": "No valid schedules found. " + ', and '.join(course_conflicts) + '.'}
        courses_dict = self._create_course_dict(courses_obj)
        (components, aliases) = self._create_components(courses_dict)
        cardinality = self._cross_prod_cardinality(components)
        print("Cross product cardinality: " + str(cardinality))
        self._build_conflicts_set(components)
        mrv_model = MRV.MRV_Model(components, self._CONFLICTS)
        mrv_model.solve()
        valid_schedules = mrv_model.get_valid_schedules()
        if len(valid_schedules) == 0:
            return {"schedules":[], "aliases":[],
                "errmsg": "No schedules to display: all schedules have time conflicts."}
        shuffle(valid_schedules)
        print(f"Exhaustive (MRV): {len(valid_schedules)}")
        sorted_schedules = self._master_sort(valid_schedules, prefs)
        return {"schedules":[[c[0] for c in s._schedule] for s in sorted_schedules], "aliases":aliases}
