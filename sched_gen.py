import query

import pycosat
from itertools import product
from random import choice, shuffle

EXHAUST_CARDINALITY_THRESHOLD = 2000000
ASSUMED_COMMUTE_TIME = 40
CONFLICTS = query.get_conflicts_set()

# param course_list is a list of strings of form "SUBJ CATALOG" e.g. "CHEM 101".
# returns a tuple (components, aliases). components is list of components where
#   a component is all classes belonging to a particular component of a course.
#   e.g. create_components(["CHEM 101"]) will find components for LEC, SEM, LAB,
#   and CSA. aliases maps string class IDs to all classes of the same component
#   that share identical start times, end times, and days, used to reduce the
#   search space to only unique "looking" schedules.
def _create_components(course_list):
    assert len(course_list) > 0, "Courses input is empty"
    assert len(set(course_list)) == len(course_list),\
        "Course list has duplicates"
    components = []
    aliases = {}
    for course in course_list:
        course_dict = query.get_course_classes(course)
        for component in course_dict.keys():
            component_classes = course_dict[component]
            new_component = []
            component_aliases = {}
            classtime_to_first_class = {}
            for component_class in component_classes:
                class_id = component_class[-1]
                class_time = (component_class[4], component_class[5],
                              component_class[6])
                if class_time in classtime_to_first_class:
                    first_class = classtime_to_first_class[class_time]
                    component_aliases[first_class].append(class_id)
                    aliases[first_class] = component_aliases[first_class]
                else:
                    classtime_to_first_class[class_time] = class_id
                    component_aliases[class_id] = []
                    new_component.append(component_class)
            components.append(new_component)
    return (components, aliases)

# 3 classes of clauses are constructed:
# 1. min_sol is conjunction of classes that must be in a solution,
#    i.e. a solution must have a class from each component.
# 2. single_sel is logical implication of the fact that if a solution
#    contains class P then all classes C in the same component of P cannot
#    be in the solution: P -> ~C1 /\ ~C2, /\ ... /\ ~Cn.
# 3. conflicts is a set of tuple lists of form [C1, C2] where C1 and C2
#    have a time conflict
def _build_cnf(components):
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
            class_a, class_b = flat_components[i][-1], flat_components[j][-1]
            if (class_a, class_b) in CONFLICTS:
                conflicts.append([-1 * (i+1), -1 * (j+1)])
                conflicts.append([-1 * (j+1), -1 * (i+1)])
    cnf = min_sol + single_sel + conflicts
    return cnf

# Given a list of components, returns the size of the cross product. This is
# useful for knowing the workload prior to computing it, which can be grow
# more than exponentially fast.
def _cross_prod_cardinality(components):
    cardinality = 1
    for component in components:
        cardinality *= len(component)
    return cardinality

# Given a schedule that is represented by a list of classes retrived from a
# database, check if it is valid by looking up the existence of
# time-conflict-pairs for every pair of classes in the schedule.
def _valid_schedule(schedule):
    class_ids = class_ids = [c[-1] for c in schedule]
    for i in range(len(class_ids)):
        for j in range(i+1, len(class_ids)):
            if (class_ids[i], class_ids[j]) in CONFLICTS:
                return False
    return True

# Given a list of schedules, filter out every schedule with time conflicts. 
def _validate_schedules(schedules):
    valid_schedules = []
    for schedule in schedules:
        if _valid_schedule(schedule):
            valid_schedules.append(schedule)
    return valid_schedules

def _closeness_evaluate(schedule):
    clean_sched = []
    for course_class in schedule:
        if course_class[4] != 2147483647:
            clean_sched.append(course_class)
    schedule = clean_sched
    day_times_map = {}
    for course_class in schedule:
        days = course_class[6]
        start_t, end_t = course_class[4], course_class[5]
        for day in days:
            if not day in day_times_map:
                day_times_map[day] = [(start_t, end_t)]
            else:
                day_times_map[day].append((start_t, end_t))
    time_not_in_class = 0
    for times in day_times_map.values():
        if len(times) == 1:
            time_not_in_class += ASSUMED_COMMUTE_TIME * 2
            continue
        times.sort()
        day_time_spent = times[-1][1] - times[0][0]
        for time_tuple in times:
            day_time_spent -= (time_tuple[1] - time_tuple[0])
        time_not_in_class += day_time_spent
    return time_not_in_class

def _sort_by_closeness(schedules):
    shuffle(schedules)
    schedule_timewasted = []
    for schedule in schedules:
        time_not_in_class = _closeness_evaluate(schedule)
        schedule_timewasted.append((schedule, time_not_in_class))
    schedule_timewasted.sort(key=lambda t: t[1])
    sorted_schedules = [s[0] for s in schedule_timewasted]
    return sorted_schedules

# Generate valid schedules for a string list of courses. First construct a
# a list of components, where a "component" is a set of classes where each
# class contains information such as class time, id, location, etc, and share
# a component if they have the same course id and component such as LEC or
# LAB. Early exit if the SAT solver proves unsatisfiability. If the size of
# possibly valid schedules is within a computational threshold T, then
# attempt to validate all schedules. If the size exceeds the threshold,
# randomly sample from every axis (component) and gather a subset of all
# possibly valid schedules of size T.
def generate_schedules(course_list):
    (components, aliases) = _create_components(course_list)
    cnf = _build_cnf(components)
    if pycosat.solve(cnf) == "UNSAT":
        return []
    cardinality = _cross_prod_cardinality(components)
    print("Cross product cardinality: " + str(cardinality))
    valid_schedules = []
    if cardinality <= EXHAUST_CARDINALITY_THRESHOLD:
        schedules = list(product(*components))
        valid_schedules = _validate_schedules(schedules)
    else:
        sampled_schedules = []
        for _ in range(EXHAUST_CARDINALITY_THRESHOLD):
            sample_sched = []
            for component in components:
                sample_sched.append(choice(component))
            sampled_schedules.append(sample_sched)
        valid_schedules = _validate_schedules(sampled_schedules)
    return _sort_by_closeness(valid_schedules)

#schedules = generate_schedules(["CMPUT 201", "CMPUT 272", "MATH 216", "MATH 217"])

