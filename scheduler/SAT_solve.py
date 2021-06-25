import numpy as np
from random import randint
from ortools.sat.python import cp_model

class VarArraySolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, components, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._components = components
        self._variables = variables
        self._valid_schedules = []
        self._solution_count = 0

    def on_solution_callback(self):
        flat_c = [j for sub in self._components for j in sub]
        flat_v = [self.Value(j) for sub in self._variables for j in sub]
        self._valid_schedules.append([y for x, y in enumerate(flat_c) if flat_v[x]])
        self._solution_count += 1

    def get_valid_schedules(self):
        return self._valid_schedules

    def solution_count(self):
        return self._solution_count

def _is_class_long(course_class):
    if course_class[1] != "LAB":
        for classtime in course_class[5]:
            if classtime[2] - classtime[1] >= 170:
                return True
    return False

def build_model(components, conflicts, randomize=True, hint=True):
    model = cp_model.CpModel()
    constraints = []
    for c_i in range(len(components)):
        outer_comp_vars = [model.NewBoolVar(f"{c_i},{j}") for j in range(len(components[c_i]))]
        constraints.append(outer_comp_vars)
        model.AddBoolOr([v for v in outer_comp_vars])
    constraint_conflict_counts = []
    for c_i in range(len(components)):
        flatten_components = [j for sub in components[c_i+1:] for j in sub]
        flatten_constraints = [j for sub in constraints[c_i+1:] for j in sub]
        for i, class_a in enumerate(components[c_i]):
            class_a_conflicts = []
            class_a_has_conflict = False
            for j, class_b in enumerate(flatten_components):
                if (class_a[0], class_b[0]) in conflicts:
                    class_a_conflicts.append(flatten_constraints[j])
                    class_a_has_conflict = True
            class_a_var = constraints[c_i][i]
            if randomize:
                model.AddHint(class_a_var, randint(0, 1))
            if len(class_a_conflicts) > 0:
                constraint_conflict_counts.append((class_a_var, len(class_a_conflicts)))
            # A class that has no conflicts outside of its component is likely to be in a solution
            if hint and not class_a_has_conflict:
                model.AddHint(class_a_var, 1)
            # Add all the other classes in this component to the list of conflicts for this class
            class_a_conflicts += list(set(constraints[c_i]) - set([class_a_var]))
            model.AddBoolAnd([v_p.Not() for v_p in class_a_conflicts]).OnlyEnforceIf(class_a_var)
    # A class that is long is likely to not be in a solution
    if hint:
        for i in range(len(components)):
            for j in range(len(components[i])):
                if _is_class_long(components[i][j]):
                    model.AddHint(constraints[i][j], 0)
    # Conflicts in the top quartile of conflict count are likely to not be in a solution
    constraint_conflict_counts.sort(key=lambda t: t[1])
    if hint and len(constraint_conflict_counts) > 0:
        bottom_quartile_index = len(constraint_conflict_counts) // 4
        top_quartile_index = len(constraint_conflict_counts) - bottom_quartile_index
        for constraint_t in constraint_conflict_counts[top_quartile_index:]:
            model.AddHint(constraint_t[0], 0)
        for constraint_t in constraint_conflict_counts[:bottom_quartile_index]:
            model.AddHint(constraint_t[0], 1)
    return model, constraints

def is_satisfiable(model):
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    return status == cp_model.OPTIMAL

def search_within_time_limit(model, components, constraints, time_lim):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_lim
    solution_printer = VarArraySolutionCollector(components, constraints)
    status = solver.SearchForAllSolutions(model, solution_printer)
    print(f"SAT: {solution_printer.solution_count()}")
    return solution_printer.get_valid_schedules(), status
