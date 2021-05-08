from query import get_course_classes

# param course_list is a list of strings of form "SUBJ CATALOG" e.g. "CHEM 101"
# returns a tuple (components, aliases). components is list of components where
#   a component is all classes belonging toa particular component of a course.
#   e.g. create_components(["CHEM 101"]) will return components for LEC, SEM, LAB,
#   and CSA. aliases maps string class IDs to all classes of the same component
#   that share identical start times, end times, and days.
def _create_components(course_list):
    components = []
    aliases = {}
    for course in course_list:
        course_dict = get_course_classes(course)
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

_create_components(["CHEM 101"])