"""
Example on how to integrate the garage_watch module with
a Raspberry PI equipped with a Raspberry Pi camera, a door
sensor and a cancel button.

It will use the following specific libraries for the
Raspberry Pi

    gpiozero  
    RPI.GPIO  # backend for gpiozero
    picamera
    requests
    twisted
"""

from twisted.internet.task import LoopingCall
from twisted.internet import reactor


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

    scheduledPrepare = None

    def start_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
        
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
        
        def prepare_finished_callback(cls):
            if cls.state == 'prepare':
                cls.prepare_finished()

        print("Scheduled call")
        self.scheduledPrepare = reactor.callLater(10, prepare_finished_callback, self)
    
    def on_exit_prepare(self):
        print("Exiting prepare")
        if self.scheduledPrepare:
            self.scheduledPrepare.cancel()
            self.scheduledPrepare = None

    def take_picture(self):
        print("Taking picture")
        self.camera.capture(
            "{}.jpg".format(datetime.now().isoformat()), 
            format='jpeg', 
            quality=82)

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

    def periodic_take_picture():
        cam_control.take_picture()

    #lc = LoopingCall(periodic_take_picture)
    #lc.start(5)

    reactor.callLater(3, lambda: cam_control.door_open())
    reactor.callLater(7, lambda: cam_control.cancel_requested())

    reactor.run()

if __name__ == "__main__":
    main()