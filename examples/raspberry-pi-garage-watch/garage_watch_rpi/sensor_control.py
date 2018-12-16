import logging

from smbus2 import SMBus
from twisted.internet.task import LoopingCall

bus = SMBus(1)

logger = logging.getLogger(__name__)

def _periodic_check_door(instance):
    try:
        try:
            bus_data = bus.read_i2c_block_data(instance.sensor_i2c_address, 0, 8)
        except OSError:
            return
        for data_byte in bus_data[0:5]:
            # check sensor events
            if data_byte == 0x01:
                instance._send_event('door_open')
            elif data_byte == 0x02:
                instance._send_event('door_closed')
            elif data_byte == 0x03:
                instance._send_event('override_button_pressed')

        # check parking mode
        parking_status = bus_data[5]
        is_valid_parking_status = 0x00 <= parking_status <= 0x09
        
        if is_valid_parking_status and (
                parking_status != 0x00 or
                instance.parking_status != 0x00):
            instance.parking_mode = (parking_status == 0x00)
            instance.parking_distance[0] = bus_data[6]
            instance.parking_distance[1] = bus_data[7]

            if parking_status != instance.parking_status:
                instance._send_event('parking_status_changed', parking_status, instance.parking_status)
                instance.parking_status = parking_status

            # call the parking callbacks
            for fn, args, kwargs in instance.parking_event_callbacks:
                fn(instance, *args, *kwargs)
                
    except:
        logger.exception("Error in _periodic_check_door")
        
        
class SensorControl(object):

    INTERVAL_REGULAR = 2
    INTERVAL_FAST = 0.5

    EVENTS = ['door_closed', 'door_open', 'override_button_pressed', 'parking_status_changed']

    event_handlers = None
    parking_event_callbacks = None
    def __init__(self, i2c_address):
        self.sensor_i2c_address = i2c_address
        self.lc = None
        self.event_handlers = {k:[] for k in self.EVENTS}
        self.parking_event_callbacks = []
        self.parking_status = 0
        self.parking_distance = [0, 0]
        self.parking_mode = False
        
    def start(self, interval=None, now=True):
        
        self.stop()
        self.lc = LoopingCall(_periodic_check_door, self)
        self.lc.start(interval or self.INTERVAL_REGULAR, now)

    def stop(self):
        if self.lc and self.lc.running:
            self.lc.stop()
        

    def add_parking_data_update_callback(self, fn, *args, **kwargs):
        self.parking_event_callbacks.append((fn, args, kwargs))
    
    def add_event_handler(self, event, fn, *args, **kwargs):
        self.event_handlers[event].append((fn, args, kwargs))
    
    def _send_event(self, event, *args, **kwargs):
        # detect special case of entering in parking mode
        # make faster reads
        if event == 'parking_status_changed':
            if args[1] == 0x00 and args[0] != 0x00:
                self.parking_mode = True
                self.start(self.INTERVAL_FAST, now=False)
                logger.info("Entering parking mode")
            elif args[0] == 0x00 and args[1] != 0x00:
                self.parking_mode = False
                self.start(self.INTERVAL_REGULAR, now=False)
                logger.info("Exiting parking mode")

        for handler in self.event_handlers.get(event, []):
            handler[0](data=(args, kwargs), *handler[1], **handler[2])
