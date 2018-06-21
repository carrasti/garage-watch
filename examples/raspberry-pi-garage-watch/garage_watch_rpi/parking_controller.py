from transitions import Machine

class ParkingController(object):
    states = ['hold', 'parking_start', 'parking_approach', 'parking_parking', 'parking_inplace', 'parking_toofar', 'exit_in_place', 'exit_backup', 'exit_complete']
    
    events_dict = {i: 'do_{}'.format(st) for i, st in enumerate(states)}
    
    def __init__(self):
        self.machine = Machine(
            model=self, 
            states=type(self).states, 
            initial='hold',
            ignore_invalid_triggers=True)
            
        for i, st in enumerate(self.states):
            self.machine.add_transition(trigger=self.events_dict[i], source='*', dest=st)
