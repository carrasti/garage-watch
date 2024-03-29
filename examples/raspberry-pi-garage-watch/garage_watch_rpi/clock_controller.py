import os
import logging
import requests

from datetime import datetime

from gpiozero import MotionSensor
from adafruit_ht16k33 import segments
import board
import busio

from twisted.internet.task import LoopingCall

from garage_watch import CameraController

# logger for the script
logger = logging.getLogger(__name__)

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

def _update_time(instance):
    """
    Update the clock, this should not fail as it is in a task
    """
    try:
        now = datetime.now()
        if now != instance.last_time:
            instance.last_time = now
            instance.seven_segment.print("{:2}{:02}".format(now.hour, now.minute))
            instance.seven_segment.show()
    except Exception as exc:
        logger.exception(exc)
        

class ClockController(CameraController):
    """
    Implementation of the controller for the clock
    """

    # create the Pi camera instance and configure it
    def __init__(self, sensor_pin, led_i2c_address):
        self.pir_sensor = MotionSensor(sensor_pin)
        self.seven_segment = segments.Seg7x4(
            i2c,
            address=led_i2c_address)
        self.seven_segment.brightness = 0.5
        self.last_time = None
        self.lc = None  # LoopingCall

        def when_motion():
            self.start_clock()

        def when_no_motion():
            self.stop_clock()
        
        self.pir_sensor.when_motion = when_motion
        self.pir_sensor.when_no_motion = when_no_motion

        if self.pir_sensor.motion_detected:
            self.start_clock()
        else:
            self.stop_clock()
            

    def start_clock(self):
        """
        Start the clock and update it every number of seconds
        """

        logger.info("Motion detected, starting clock")
        self.seven_segment.colon = True
        
        if self.lc and self.lc.running:
            self.lc.stop()
        self.lc = LoopingCall(_update_time, self)
        self.lc.start(5, True)  # update every 5 seconds

    def stop_clock(self):
        """
        Stop the clock and clear the display
        """
        logger.info("No motion, stopping clock")
        if self.lc and self.lc.running:
            self.lc.stop()

        self.seven_segment.colon = False
        self.seven_segment.fill(0)
        self.seven_segment.show()
