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
from signal import pause
from datetime import datetime

from garage_watch import CameraController
from gpiozero import Button
from picamera import PiCamera


class GarageCameraController(CameraController):
    """
    Implementation of the controller using the raspberry PI
    """

    # create the Pi camera instance and configure it
    camera = PiCamera()
    camera.resolution = (1280, 720)
    camera.framerate = 5

    def start_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
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

    def prepare_recording(self):
        """
        Wait 10 seconds before start recording
        """
        from time import sleep
        # FIXME: something async better than a sleep
        sleep(10)
        self.prepare_finished()


def main():
    """
    The main execution function for this script
    """
    # define the magnetic door sensor connected to pin 14
    door_sensor = Button(14, bounce_time=0.5)

    # define the cancel momentary push button connected to pin 27
    cancel_button = Button(27, bounce_time=0.5)

    # create the camera controller instance
    cam_control = GarageCameraController()

    # hook door sensor press/released callbacks to the camera controller
    door_sensor.when_pressed = lambda: cam_control.door_open()
    door_sensor.when_released = lambda: cam_control.door_closed()

    # hook cancel button pressed callbacks to the camera controller
    cancel_button.when_pressed = lambda: cam_control.cancel_button_pressed()

    # kick off if the door is open when the script is run
    if door_sensor.is_pressed:
        door_sensor.when_pressed()

    pause()

if __name__ == "__main__":
    main()
