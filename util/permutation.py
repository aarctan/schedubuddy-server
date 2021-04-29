from query import get_course_classes
import itertools

def no_sched_conflict(sched):
    ranges = []
    for course in sched:
        for course_class in course:
            ranges.append((course_class[4], course_class[5]))
    ranges.sort(key=lambda t: t[0])
    for i in range(len(ranges)-1):
        if ranges[i+1][0] < ranges[i][0]:
            return False
    print(ranges)
    return True

def permute_classes(str_courses):
    course_prods = []
    for str_course in str_courses:
        course_classes = get_course_classes(str_course)
        components = course_classes.values()
        cross_prod = list(itertools.product(*components))
        course_prods.append(cross_prod)
    sched_prod = list(itertools.product(*course_prods))
    valid_schedules = []
    for sched in sched_prod:
        if no_sched_conflict(sched):
            valid_schedules.append(sched)
    for valid_sched in valid_schedules:
        print(valid_sched)



permute_classes(["CHEM 102", "CMPUT 175"])

