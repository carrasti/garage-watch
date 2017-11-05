"""
Example on how to integrate the garage_watch module with
a Raspberry PI equipped with a Raspberry Pi camera, a door
sensor and a cancel button.

It will use the following specific libraries for the
Raspberry Pi

    gpiozero  
    RPI.GPIO  # backend for gpiozero
    picamera
"""
import logging

from signal import pause
from datetime import datetime

from garage_watch import CameraController
from gpiozero import Button
from picamera import PiCamera

# logger for the script
logger = logging.getLogger(__name__)

# set up logging to print to console
logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)
# disable logging of transitions module
logging.getLogger('transitions').setLevel(logging.ERROR)


class GarageCameraController(CameraController):
    """
    Implementation of the controller using the raspberry PI
    """

    # create the Pi camera instance and configure it
    camera = PiCamera()

    def start_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
        self.camera.resolution = (1280, 720)
        self.camera.framerate = 5
        self.camera.start_preview()
        self.camera.start_recording(
            "{}.h264".format(datetime.now().isoformat()),
            quality=25
        )

    def stop_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
        self.camera.stop_recording()
        self.camera.stop_preview()

    def prepare_recording(self):
        """
        Wait 10 seconds before start recording
        """
        from time import sleep
        # FIXME: something async better than a sleep
        logger.info("Waiting 10 seconds before starting recording")
        sleep(10)
        # if still in prepare state send the event 
        # (might have been cancelled while waiting)
        if self.state == 'prepare':
            self.prepare_finished()


def main():
    """
    The main execution function for this script
    """
    # define the magnetic door sensor connected to pin 14
    door_sensor = Button(14)

    # define the cancel momentary push button connected to pin 27
    cancel_button = Button(27)
	
    # create the camera controller instance
    cam_control = GarageCameraController()

    # hook door sensor press/released callbacks to the camera controller
    door_sensor.when_pressed = lambda: cam_control.door_open()
    door_sensor.when_released = lambda: cam_control.door_closed()

    # hook cancel button pressed callbacks to the camera controller
    cancel_button.when_pressed = lambda: cam_control.cancel_requested()



    # kick off if the door is open when the script is run
    if door_sensor.is_pressed:
        door_sensor.when_pressed()

    pause()

if __name__ == "__main__":
    main()
