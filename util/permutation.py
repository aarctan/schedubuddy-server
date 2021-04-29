from query import get_course_classes
import itertools

day_lookup = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}
def valid_schedule(sched):
    ranges = []
    for course in sched:
        for course_class in course:
            start_t, end_t = course_class[4], course_class[5]
            for day in course_class[6]:
                day_mult = day_lookup[day]
                ranges.append((start_t + 2400*day_mult, end_t + 2400*day_mult))
    ranges.sort(key=lambda t: t[0])
    for i in range(len(ranges)-1):
        if ranges[i+1][0] < ranges[i][1]:
            return False
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
        if valid_schedule(sched):
            valid_schedules.append(sched)
    return valid_schedules

#schedules = permute_classes(["CHEM 101", "STAT 151", "PSYCO 258", "PSYCO 223", "PSYCO 275"])
schedules = permute_classes(["CMPUT 397", "CMPUT 355", "PSYCO 258", "PSYCO 223", "PSYCO 275"])

for schedule in schedules:
    for course in schedule:
        print(course)
    print()
print(len(schedules))



