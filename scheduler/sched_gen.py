import pycosat
import numpy as np
from itertools import product, combinations, islice
import functools
from random import choice, shuffle, sample, randint
from joblib import Parallel, delayed

EXHAUST_CARDINALITY_THRESHOLD = 350000
ASSUMED_COMMUTE_TIME = 40
IDEAL_CONSECUTIVE_LENGTH = 3*60

def str_t_to_int(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

DEFAULT_PREFS = {
    "EVENING_CLASSES": True,
    "ONLINE_CLASSES": True,
    "IDEAL_START_TIME": 10,
    "IDEAL_CONSECUTIVE_LENGTH": 3,
    "LIMIT": 30
}

class ValidSchedule:
    def __init__(self, schedule, aliases, blocks, num_pages, prefs):
        self._schedule = schedule
        self._aliases = aliases
        self._blocks = blocks
        self._num_pages = num_pages
        self.time_variance = self.compute_time_variance()
        self.time_wasted = self.compute_time_wasted()
        self.gap_err = self.compute_gap_err(prefs["IDEAL_CONSECUTIVE_LENGTH"])
        self.start_err = self.compute_start_err(prefs["IDEAL_START_TIME"])
        self.time_wasted_rank = None
        self.time_var_rank = None
        self.gap_err_rank = None
        self.start_err_rank = None

        self.overall_rank = None
        self.score = None

    def compute_gap_err(self, ideal):
        ideal = ideal*60
        GVE = 0
        for day_blocks in self._blocks.values():
            for block in day_blocks:
                block_len = block[1] - block[0]
                if block_len <= ideal:
                    GVE += (ideal - block_len)**2
                else:
                    # greatly discourage very long marathons
                    GVE += (block_len - ideal)**3
        return GVE
    
    def compute_start_err(self, ideal):
        ideal = ideal*60
        error = 0
        for day in self._blocks.keys():
            day_start_t = self._blocks[day][0][0]
            if day_start_t < ideal:
                # discourage very early starts
                error += ((ideal - day_start_t) ** 3)
            else:
                error += (self._blocks[day][0][0] - ideal) ** 2
        return error / (len(self._blocks.keys()))
    
    def compute_time_variance(self):
        start_times, end_times = [], []
        for day in self._blocks.keys():
            start_times.append(self._blocks[day][0][0])
            end_times.append(self._blocks[day][-1][1])
        return np.var(start_times)*1.5 + np.var(end_times)
    
    def compute_time_wasted(self):
        time_wasted = 0
        for day in self._blocks.keys():
            time_wasted += ASSUMED_COMMUTE_TIME * 2
            day_blocks = self._blocks[day]
            day_time_wasted = day_blocks[-1][1] - day_blocks[0][0]
            for block in day_blocks:
                day_time_wasted -= block[1] - block[0]
            time_wasted += day_time_wasted
        return time_wasted
    
    def get_gap_err(self):
        return self.gap_err
    
    def get_time_variance(self):
        return self.time_variance

    def set_overall_rank(self):
        combined_rank = self.time_wasted_rank +\
            self.gap_err_rank +\
            self.time_var_rank
        self.score = round(((combined_rank / (self._num_pages*3)) * 5), 2)

        adjusted_combined_rank =\
            self.time_wasted_rank*1 +\
            self.time_var_rank*1 +\
            self.gap_err_rank*1 +\
            self.start_err_rank*1
        self.adjusted_score = adjusted_combined_rank
        #self.adjusted_score = round(((adjusted_combined_rank / (self._num_pages*1)) * 5), 2)
    
    def get_schedule(self):
        return self._schedule

class ScheduleFactory:
    def __init__(self, exhaust_threshold=500000):
        self._EXHAUST_CARDINALITY_THRESHOLD = exhaust_threshold
        self._day_index = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}
        self._CONFLICTS = set()

    def _conflicts(self, class_a, class_b):
        class_a_id, class_b_id = class_a[0], class_b[0]
        if (class_a_id, class_b_id) in self._CONFLICTS:
            return True
        ranges = []
        for course_class in (class_a, class_b):
            classtimes = course_class[5]
            for classtime in classtimes:
                start_t, end_t = classtime[1], classtime[2]
                for day in classtime[0]:
                    day_mult = self._day_index[day]
                    ranges.append((start_t + 2400*day_mult, end_t + 2400*day_mult))
        ranges.sort(key=lambda t: t[0])
        for i in range(len(ranges)-1):
            if ranges[i][1] > ranges[i+1][0]:
                self._CONFLICTS.add((class_a_id, class_b_id))
                self._CONFLICTS.add((class_b_id, class_a_id))
                return True
        return False

    def _json_sched(self, sched):
        return [c[0] for c in sched]

    # 3 classes of clauses are constructed:
    # 1. min_sol is conjunction of classes that must be in a solution,
    #    i.e. a solution must have a class from each component.
    # 2. single_sel is logical implication of the fact that if a solution
    #    contains class P then all classes C in the same component of P cannot
    #    be in the solution: P -> ~C1 /\ ~C2, /\ ... /\ ~Cn.
    # 3. conflicts is a set of tuple lists of form [C1, C2] where C1 and C2
    #    have a time conflict
    def _build_cnf(self, components):
        min_sol = []
        single_sel = []
        flat_idx = 1
        for component in components:
            component_min_sol = list(range(flat_idx, len(component)+flat_idx))
            flat_idx += len(component)
            min_sol.append(component_min_sol)
            not_min_sol = [-1 * e for e in component_min_sol]
            component_single_sel = []
            for i_ss in range(len(not_min_sol)):
                for j_ss in range(i_ss+1, len(not_min_sol)):
                    if i_ss != j_ss:
                        component_single_sel.append(\
                            [not_min_sol[i_ss], not_min_sol[j_ss]])
                        component_single_sel.append(\
                            [not_min_sol[j_ss], not_min_sol[i_ss]])
            single_sel += component_single_sel
        flat_components = [e for c in components for e in c]
        conflicts = []
        for i in range(len(flat_components)):
            for j in range(i+1, len(flat_components)):
                class_a, class_b = flat_components[i][0], flat_components[j][0]
                if (class_a, class_b) in self._CONFLICTS:
                    conflicts.append([-1 * (i+1), -1 * (j+1)])
                    conflicts.append([-1 * (j+1), -1 * (i+1)])
        cnf = min_sol + single_sel + conflicts
        return cnf

    # Given a list of components, returns the size of the cross product. This is
    # useful for knowing the workload prior to computing it, which can be grow
    # more than exponentially fast.
    def _cross_prod_cardinality(self, components):
        cardinality = 1
        for component in components:
            cardinality *= len(component)
        return cardinality

    # Given a schedule that is represented by a list of classes retrived from a
    # database, check if it is valid by looking up the existence of
    # time-conflict-pairs for every pair of classes in the schedule.
    def _valid_schedule(self, schedule):
        class_ids = class_ids = [c[0] for c in schedule]
        for i in range(len(class_ids)):
            for j in range(i+1, len(class_ids)):
                if (class_ids[i], class_ids[j]) in self._CONFLICTS:
                    return False
        return True

    # Given a list of schedules, filter out every schedule with time conflicts. 
    def _validate_schedules(self, schedules):
        valid_schedules = []
        for schedule in schedules:
            if self._valid_schedule(schedule):
                valid_schedules.append(schedule)
        return valid_schedules

    def _get_schedule_blocks(self, schedule):
        clean_sched = []
        for course_class in schedule:
            has_time_null = False
            for time_tuple in course_class[5]:
                start_t = time_tuple[1]
                if start_t == 2147483647:
                    has_time_null = True
            if not has_time_null:
                clean_sched.append(course_class)
        schedule = clean_sched
        day_times_map = {}
        for course_class in schedule:
            for time_tuple in course_class[5]:
                days, start_t, end_t, _ = time_tuple
                for day in days:
                    if not day in day_times_map:
                        day_times_map[day] = [(start_t, end_t)]
                    else:
                        day_times_map[day].append((start_t, end_t))
        for times in day_times_map.values():
            if len(times) == 1:
                continue
            times.sort()
            i = 0
            while i <= len(times)-2:
                t_i, t_j = times[i], times[i+1]
                if t_j[0] - t_i[1] <= 15:
                    times[i] = (t_i[0], t_j[1])
                    del times[i+1]
                    i -= 1
                i += 1
        return day_times_map

    def _master_sort(self, schedules, prefs):
        sched_objs = []
        num_pages = len(schedules)
        for schedule in schedules:
            blocks = self._get_schedule_blocks(schedule)
            sched_obj = ValidSchedule(schedule, [], blocks, num_pages, prefs)
            sched_objs.append(sched_obj)
        time_var_sorted = sorted(sched_objs, key=lambda SO: SO.time_variance, reverse=True)
        time_waste_sorted = sorted(sched_objs, key=lambda SO: SO.time_wasted, reverse=True)
        gap_err_sorted = sorted(sched_objs, key=lambda SO: SO.gap_err, reverse=True)
        start_err_sorted = sorted(sched_objs, key=lambda SO: SO.start_err, reverse=True)
        for i, sched_obj in enumerate(gap_err_sorted):
            sched_obj.gap_err_rank = i+1
        for i, sched_obj in enumerate(time_var_sorted):
            sched_obj.time_var_rank = i+1
        for i, sched_obj in enumerate(time_waste_sorted):
            sched_obj.time_wasted_rank = i+1
        for i, sched_obj in enumerate(start_err_sorted):
            sched_obj.start_err_rank = i+1
        for sched_obj in sched_objs:
            sched_obj.set_overall_rank()
        overall_sorted = sorted(sched_objs, key=lambda SO: SO.adjusted_score, reverse=True)
        overall_sorted = overall_sorted[:min(prefs["LIMIT"], num_pages)]
        #shuffle(overall_sorted)
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
                        class_times.append((component_class[5][i][:3]))
                    class_times = tuple(class_times)
                    if class_times in classtime_to_first_class:
                        first_class = classtime_to_first_class[class_times]
                        component_aliases[first_class].append(class_comp_str)
                        aliases[first_class] = component_aliases[first_class]
                    else:
                        first_class_key = component_class[0] + ' ' + class_comp_str
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
                        course_class["location"]))
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

    def product(self, *sequences):
        '''Breadth First Search Cartesian Product'''
        # sequences = tuple(tuple(seq) for seqin sequences)
        def partitions(n, k):
            for c in combinations(range(n+k-1), k-1):
                yield (b-a-1 for a, b in zip((-1,)+c, c+(n+k-1,)))
        max_position = [len(i)-1 for i in sequences]
        for i in range(sum(max_position)):
            for positions in partitions(i, len(sequences)):
                try:
                    yield tuple(map(lambda seq, pos: seq[pos], sequences, positions))
                except IndexError:
                    continue
        yield tuple(map(lambda seq, pos: seq[pos], sequences, max_position))

    # Generate valid schedules for a string list of courses. First construct a
    # a list of components, where a "component" is a set of classes where each
    # class contains information such as class time, id, location, etc, and share
    # a component if they have the same course id and component such as LEC or
    # LAB. Early exit if the SAT solver proves unsatisfiability. If the size of
    # possibly valid schedules is within a computational threshold T, then
    # attempt to validate all schedules. If the size exceeds the threshold,
    # randomly sample from every axis (component) and gather a subset of all
    # possibly valid schedules of size T.
    def generate_schedules(self, courses_obj, prefs=DEFAULT_PREFS):
        courses_dict = self._create_course_dict(courses_obj)
        (components, aliases) = self._create_components(courses_dict)
        self._build_conflicts_set(components)
        cnf = self._build_cnf(components)
        if pycosat.solve(cnf) == "UNSAT":
            return []
        cardinality = self._cross_prod_cardinality(components)
        print("Cross product cardinality: " + str(cardinality))
        valid_schedules = []
        if cardinality <= EXHAUST_CARDINALITY_THRESHOLD:
            schedules = list(product(*components))
            valid_schedules = self._validate_schedules(schedules)
        else:
            sampled_schedules = []
            for _ in range(EXHAUST_CARDINALITY_THRESHOLD):
                sample_sched = []
                for component in components:
                    sample_sched.append(choice(component))
                sampled_schedules.append(sample_sched)
            valid_schedules = self._validate_schedules(sampled_schedules)
        sorted_schedules = self._master_sort(valid_schedules, prefs)
        return {"schedules":[[c[0] for c in s._schedule] for s in sorted_schedules], "aliases":aliases}

