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
    scp (+ paramiko)
"""

import logging
import os
import argparse


from logging.handlers import TimedRotatingFileHandler

from twisted.internet.task import LoopingCall
from twisted.internet import reactor

from garage_watch_rpi.camera_controller import GarageCameraController
from garage_watch_rpi.sensor_control import SensorControl
from garage_watch_rpi.parking_controller_led import LEDParkingController
from garage_watch_rpi.clock_controller import ClockController

from garage_watch_rpi.mqtt_controller import MQTTService

# logger for the script
logger = logging.getLogger(__name__)

# environment variables with secrets
def main():
    """
    The main execution function for this script
    """
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-dir", 
        default='',
        type=str, 
        help="the base directory for snapshots")
    parser.add_argument(
        "--video-dir", 
        type=str, 
        default='',
        help="the base directory for storing video recordings")
    
    parser.add_argument(
        "--log-dir", 
        type=str, 
        default='console',
        help="the base directory to store logs")

    parser.add_argument(
        "--upload-url", 
        type=str, 
        default='',
        help="the url to send the file to")
    
    parser.add_argument(
        "--upload-auth-jwk-path", 
        type=str, 
        default='',
        help="the path to serialized jwk for jwt authentication")


    args = parser.parse_args()

    logconfig_kwargs = {}
    
    if args.log_dir != 'console':
        # configure logging 
        # rotating file handler, 5 MB per file
        trfh = TimedRotatingFileHandler(
            os.path.join(args.log_dir, 'garage-camera.log'),
            when='midnight',
            backupCount=14,
        )
        logconfig_kwargs['handlers'] = [trfh]

    # set up logging to print to console
    logging.basicConfig(
        format='[%(levelname)s][%(asctime)s][%(name)s] %(message)s',
        level=logging.INFO,
        **logconfig_kwargs
    )
    # disable logging of transitions module
    logging.getLogger('transitions').setLevel(logging.ERROR)
    # disable logging of scp module
    logging.getLogger('twisted').setLevel(logging.INFO)

    mqtt_service = MQTTService(reactor)
    mqtt_service.startService()
    # default value for door on connected
    mqtt_service.whenConnected().addCallback(lambda *args: mqtt_service.report_door_closed())

    PUSHBULLET_SECRET = os.environ.get('PUSHBULLET_SECRET', None)
    if not PUSHBULLET_SECRET:
        logger.warning(
            "PUSHBULLET_SECRET environment variable not set. Messages will not be sent")


    if not args.upload_url or not args.upload_auth_jwk_path:
        
        logger.warning(
            "Upload improperly configured. Snapshots will not be uploaded")

    # create the camera controller instance
    cam_control = GarageCameraController()
    # configure output dirs
    cam_control.snapshot_dir = args.snapshot_dir
    cam_control.video_dir = args.video_dir
    cam_control.upload_url = args.upload_url
    cam_control.upload_auth_jwk_path = args.upload_auth_jwk_path
    cam_control.pushbullet_secret = PUSHBULLET_SECRET

    # configure periodically taking a picture
    def periodic_take_picture():
        picture_stream = cam_control.take_picture()
        cam_control.upload_picture(picture_stream)
        cam_control.save_picture(picture_stream)

    def periodic_report_door_status():
        # report status of door open based on door sensor
        if not mqtt_service.connected or not sc:
            return
        if sc.is_door_open():
            mqtt_service.report_door_open()
        else:
            mqtt_service.report_door_closed()

    lc = LoopingCall(periodic_take_picture)
    lc.start(60)
    
    lc = LoopingCall(periodic_report_door_status)
    lc.start(60)
    
    # define the matrix for parking
    parking_control = LEDParkingController(rotation=180, i2c_address=0x70)
    def parking_control_status_changed(data, *args, **kwargs):
        new_state, old_state = data[0]
        ev = parking_control.events_dict.get(new_state)
        if not ev:
            return
        # debug
        # print(ev)
        # send the event
        fn = getattr(parking_control, ev)
        fn()

    def parking_control_update_callback(sc, *args, **kwargs):
        # DEBUG:
        # print(sc.parking_distance)
        # parking_control.write_amounts(sc.parking_distance[0], sc.parking_distance[1])
        pass

    def door_open_handler(*args, **kwargs):
        cam_control.door_open()
        mqtt_service.report_door_open()

    def door_close_handler(*args, **kwargs):
        cam_control.door_closed()
        mqtt_service.report_door_closed()
        
    def override_button_handler(*args, **kwargs):
        cam_control.cancel_requested()
    
    sc = SensorControl(0x27)
    sc.add_event_handler('parking_status_changed', parking_control_status_changed, sc=sc)
    sc.add_parking_data_update_callback(parking_control_update_callback)

    sc.add_event_handler('door_closed', door_close_handler)
    sc.add_event_handler('door_open', door_open_handler)
    sc.add_event_handler('override_button_pressed', override_button_handler)

    # clock with PIR sensor in pin 22 and led in 0x71
    cc = ClockController(22, 0x71)
    
    sc.start()
    
    # and kick off the reactor
    reactor.run()

if __name__ == "__main__":
    main()

