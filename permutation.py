from query import get_course_classes, get_conflicts_set
from random import shuffle
from itertools import product, islice

day_lookup = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}
conflicts = get_conflicts_set()

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

def valid_schedule2(sched):
    class_ids = []
    for course in sched:
        for course_class in course:
            class_ids.append(course_class[9])
    for i in range(len(class_ids)):
        for j in range(i+1, len(class_ids)):
            if (class_ids[i], class_ids[j]) in conflicts:
                return False
    return True

def permute_classes(str_courses, limit=None):
    course_prods = []
    for str_course in str_courses:
        course_classes = get_course_classes(str_course)
        components = course_classes.values()
        for course_class in components:
            times = set()
            prune_indices = []
            for i, c in enumerate(course_class):
                class_times = (c[4], c[5], c[6])
                if class_times in times:
                    prune_indices.append(i)
                times.add(class_times)
            prune_indices.reverse()
            for i in prune_indices:
                course_class.pop(i)
        cross_prod = list(product(*components))
        shuffle(cross_prod)
        course_prods.append(cross_prod)

    cardinality = 1
    for course in course_prods:
        cardinality *= len(course)
    print(cardinality)

    #sched_prod = list(islice(product(*course_prods), 100000))
    sched_cross_prod = product(*course_prods)
    valid_schedules = []
    for sched in sched_cross_prod:
        if valid_schedule2(sched):
            valid_schedules.append(sched)

    return valid_schedules

#schedules = permute_classes(["CHEM 101", "STAT 151", "MATH 134", "PSYCO 223", "PSYCO 275"])
#schedules = permute_classes(["CMPUT 397", "CMPUT 355", "PSYCO 258", "PSYCO 223", "PSYCO 275"])
