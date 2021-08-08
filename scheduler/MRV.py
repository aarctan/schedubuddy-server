class MRV_Model:
    def __init__(self, components, conflicts):
        self._components = components
        self._components.sort(key=len)
        self._conflicts = conflicts
        self._depth = len(self._components) - 1
        self.valid_schedules = []
    
    def get_valid_schedules(self):
        return self.valid_schedules

    def solve(self, curr=[], index=0):
        for c in self._components[index]:
            valid_pick = True
            for c_i in curr:
                if (c[0], c_i[0]) in self._conflicts:
                    valid_pick = False
                    break
            if not valid_pick:
                continue
            if index == self._depth:
                self.valid_schedules += [curr + [c]]
            if index < self._depth:
                self.solve(curr + [c], index+1)
