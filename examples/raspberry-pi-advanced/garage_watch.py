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


from logging.handlers import RotatingFileHandler

from twisted.internet.task import LoopingCall
from twisted.internet import reactor

from garage_watch_rpi_advanced.camera_controller import GarageCameraController
from garage_watch_rpi_advanced.sensor_control import SensorControl
from garage_watch_rpi_advanced.parking_controller_led import LEDParkingController

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
        "--upload-host", 
        type=str, 
        default='',
        help="the host to upload the file to via scp")
    
    parser.add_argument(
        "--upload-host-username", 
        type=str, 
        default='',
        help="the username in the host host to upload the file to via scp")

    parser.add_argument(
        "--upload-dest-filename", 
        type=str, 
        default='',
        help="the full path of the file destination in target host")

    args = parser.parse_args()

    logconfig_kwargs = {}
    
    if args.log_dir != 'console':
        # configure logging 
        # rotating file handler, 5 MB per file
        rfh = RotatingFileHandler(
            os.path.join(args.log_dir, 'garage-camera.log'),
            maxBytes=(5 * 2 ** 20)
        )
        logconfig_kwargs['handlers'] = [rfh]

    # set up logging to print to console
    logging.basicConfig(
        format='[%(levelname)s][%(asctime)s] %(message)s', 
        level=logging.INFO,
        **logconfig_kwargs
    )
    # disable logging of transitions module
    logging.getLogger('transitions').setLevel(logging.ERROR)
    # disable logging of scp module
    logging.getLogger('paramiko').setLevel(logging.ERROR)
    # disable logging of scp module
    logging.getLogger('twisted').setLevel(logging.INFO)
    
    PUSHBULLET_SECRET = os.environ.get('PUSHBULLET_SECRET', None)
    if not PUSHBULLET_SECRET:
        logger.warning(
            "PUSHBULLET_SECRET environment variable not set. Messages will not be sent")

    if not args.upload_host or not args.upload_dest_filename:
        logger.warning(
            "Upload via SCP improperly confgured. Snapshots will not be uploaded")

    # create the camera controller instance
    cam_control = GarageCameraController()
    # configure output dirs
    cam_control.snapshot_dir = args.snapshot_dir
    cam_control.video_dir = args.video_dir
    cam_control.upload_host = args.upload_host
    cam_control.upload_host_username = args.upload_host_username
    cam_control.upload_dest_filename = args.upload_dest_filename
    cam_control.pushbullet_secret = PUSHBULLET_SECRET

    # configure periodically taking a picture
    def periodic_take_picture():
        cam_control.take_picture()
    lc = LoopingCall(periodic_take_picture)
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

    def door_close_handler(*args, **kwargs):
        cam_control.door_closed()
        
    def override_button_handler(*args, **kwargs):
        cam_control.cancel_requested()
    
    sc = SensorControl(0x27)
    sc.add_event_handler('parking_status_changed', parking_control_status_changed, sc=sc)
    sc.add_parking_data_update_callback(parking_control_update_callback)

    sc.add_event_handler('door_closed', door_close_handler)
    sc.add_event_handler('door_open', door_open_handler)
    sc.add_event_handler('override_button_pressed', override_button_handler)

    
    
    sc.start()
    
    # and kick off the reactor
    reactor.run()

if __name__ == "__main__":
    main()

