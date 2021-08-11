from random import shuffle

class MRV_Model:
    def __init__(self, components, conflicts):
        self._components = components
        self._components.sort(key=len)
        for i in range(len(self._components)):
            shuffle(self._components[i])
        self._conflicts = conflicts
        self._depth = len(self._components) - 1
        self.valid_schedules = []
        self._valid_sched_count = 0
    
    def get_valid_schedules(self):
        return self.valid_schedules

    def _mrv_solve(self, curr, index):
        for c in self._components[index]:
            valid_pick = True
            for c_i in curr:
                if (c[0], c_i[0]) in self._conflicts:
                    valid_pick = False
                    break
            if not valid_pick:
                continue
            if index == self._depth:
                self.valid_schedules.append(tuple(curr + [c]))
                self._valid_sched_count += 1
            if index < self._depth:
                if self._valid_sched_count <= 125000:
                    self._mrv_solve(curr + [c], index+1)

    def solve(self):
        self._mrv_solve([], 0)
