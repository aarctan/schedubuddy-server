from query import get_course_classes
import itertools

def days_there_are_classes(classes):
    days = set([])
    for course_class in classes:
        for day in course_class[6]:
            days.add(day)
    return days

def conflict_on_day(classes):
    ranges = []
    for course_class in classes:
        ranges.append((course_class[4], course_class[5]))
    ranges.sort(key=lambda t: t[0])
    for i in range(len(ranges)-1):
        if ranges[i+1][0] < ranges[i][0]:
            return True
    return False

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
        classes = []
        for course in sched:
            for course_class in course:
                classes.append(course_class)
        class_days = days_there_are_classes(classes)
        valid_sched = True
        for day in class_days:
            classes_on_day = []
            for course_class in classes:
                if day in course_class[6]:
                    classes_on_day.append(course_class)
            if conflict_on_day(classes_on_day):
                valid_sched = False
                break
        if valid_sched:
            valid_schedules.append(sched)
    return valid_schedules


schedules = permute_classes(["CHEM 102", "CHEM 261"])
for schedule in schedules:
    print(schedule)
    print()


