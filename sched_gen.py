import query

import pycosat

EXHAUST_CARDINALITY_THRESHOLD = 100000
CONFLICTS = query.get_conflicts_set()

# param course_list is a list of strings of form "SUBJ CATALOG" e.g. "CHEM 101".
# returns a tuple (components, aliases). components is list of components where
#   a component is all classes belonging to a particular component of a course.
#   e.g. create_components(["CHEM 101"]) will find components for LEC, SEM, LAB,
#   and CSA. aliases maps string class IDs to all classes of the same component
#   that share identical start times, end times, and days, used to reduce the
#   search space to only unique "looking" schedules.
def _create_components(course_list):
    assert len(course_list) > 0, "Courses input must be non-empty"
    assert len(set(course_list)) == len(course_list),\
        "Course list must have no duplicates"
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

def _cross_prod_cardinality(components):
    cardinality = 1
    for component in components:
        cardinality *= len(component)
    return cardinality

def _components_satisfiable(cnf):
    sol = pycosat.solve(cnf)
    return sol != "UNSAT"

def generate_schedules(course_list):
    (components, aliases) = _create_components(course_list)
    cnf = _build_cnf(components)
    if not _components_satisfiable(cnf):
        return 0
    else:
        return 1

    cardinality = _cross_prod_cardinality(components)
    if cardinality <= EXHAUST_CARDINALITY_THRESHOLD:
        pass
    else:
        pass

x = generate_schedules(["CHEM 101", "CHEM 102"])
print(x)


