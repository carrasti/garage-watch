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
import requests
import argparse

from logging.handlers import RotatingFileHandler

from twisted.internet.task import LoopingCall
from twisted.internet import reactor

from datetime import datetime
from garage_watch import CameraController
from gpiozero import Button
from picamera import PiCamera


# logger for the script
logger = logging.getLogger(__name__)


# environment variables with secrets
PUSHBULLET_SECRET = None

class GarageCameraController(CameraController):
    """
    Implementation of the controller using the raspberry PI
    """

    # create the Pi camera instance and configure it
    camera = PiCamera()
    camera.resolution = (1280, 720)
    camera.annotate_text_size = 12
    scheduledPrepare = None

    snapshot_dir = ''
    video_dir = ''

    upload_host = ''
    upload_host_username = ''
    upload_dest_filename = ''

    last_video_filename = None

    def start_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
        now = datetime.now()
        # get directory for today and create if it doesn't exist
        todaydir = os.path.join(
            self.video_dir, now.strftime('%Y'), now.strftime('%m'), now.strftime('%d'))
        if not os.path.exists(todaydir):
            os.makedirs(todaydir)

        # generate the filename
        filepath = os.path.join(
            todaydir, now.strftime('%H-%M-%S.h264'))
            
        self.camera.framerate = 5
        self.camera.start_recording(filepath, quality=25)
        self.last_video_filename = filepath

    def stop_recording(self):
        """
        Kick off recording with the raspberry camera, it will
        use a video with filename the current timestamp
        """
        self.camera.stop_recording()
        
        # create a simbolyc link in the directory
        symlink_path = os.path.join(self.video_dir, 'latest_recording.h264')
        if os.path.lexists(symlink_path):
            os.unlink(symlink_path)
        os.symlink(self.last_video_filename, symlink_path)

    def prepare_recording(self):
        """
        Wait 10 seconds before start recording, if the timeout
        happens, send a message notifying of door open
        """

        def prepare_finished_callback(cls):
            if cls.state == 'prepare':
                # notify pushbullet
                if PUSHBULLET_SECRET:
                    now = datetime.now()
                    requests.post(
                        'https://api.pushbullet.com/v2/pushes',
                        auth=(PUSHBULLET_SECRET, ''),
                        json={
                            "type": "note",
                            "title": "Recording of the garage started",
                            "body": "The door opened at {}".format(
                                now.strftime("%H:%M")
                            )
                    })

                cls.prepare_finished()
        logger.info("Waiting 10 seconds before starting recording")
        self.scheduledPrepare = reactor.callLater(10, prepare_finished_callback, self)

    
    def on_exit_prepare(self):
        if self.scheduledPrepare and not self.scheduledPrepare.called:
            self.scheduledPrepare.cancel()
        if self.scheduledPrepare:
            self.scheduledPrepare = None

    def take_picture(self):
        try:
            now = datetime.now()
            # get directory for today and create if it doesn't exist
            
            todaydir = os.path.join(
                now.strftime('%Y'), now.strftime('%m'), now.strftime('%d'))
            destdir = os.path.join(self.snapshot_dir, todaydir)
            filename = now.strftime('%H-%M-%S.jpg')
            
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            # generate the filename
            filepath = os.path.join(
                destdir, filename)
            
            # capture the snapshot
            self.camera.annotate_text = now.strftime('%Y-%m-%d %H:%M')
            self.camera.capture(
                filepath,
                format='jpeg',
                quality=82,
                use_video_port=(True if self.state == 'record' else False))
            self.camera.annotate_text = ''
            logger.info("Snapshot taken")
            
            # create a simbolyc link in the directory
            symlink_path = os.path.join(self.snapshot_dir, 'latest_snapshot.jpg')
            if os.path.lexists(symlink_path):
                os.unlink(symlink_path)
            os.symlink(os.path.join(todaydir, filename), symlink_path)

            self.upload_picture(filepath)
            
        except Exception :
            logger.exception("Error taking snapshot")

    def upload_picture(self, filepath):
        """
        Upload the file on the given path to the server
        via scp

        Uses class configuration to determine the server and
        user to connect to. Relies on user public key installed
        on the target server for authentication
        """
        from paramiko import SSHClient
        from scp import SCPClient

        # skip if improperly configured    
        if not self.upload_host or not self.upload_dest_filename:
            return

        try:
            # configure ssh transport
            ssh = SSHClient()
            ssh.load_system_host_keys()
            connect_kwargs = {}
            if self.upload_host_username:
                connect_kwargs['username'] = self.upload_host_username
            ssh.connect(self.upload_host, **connect_kwargs)

            # Configure scp and perform upload
            scp = SCPClient(ssh.get_transport())
            scp.put(filepath, self.upload_dest_filename)
            
            # clean up
            scp.close()
            ssh.close()

            # log success
            logger.info("Snapshot uploaded")
        except Exception:
            logger.exception("Error uploading snapshot")

def main():
    """
    The main execution function for this script
    """
    global PUSHBULLET_SECRET

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
    logging.getLogger('paramiko').setLevel(logging.ERROR)

    PUSHBULLET_SECRET = os.environ.get('PUSHBULLET_SECRET', None)
    if not PUSHBULLET_SECRET:
        logger.warning(
            "PUSHBULLET_SECRET environment variable not set. Messages will not be sent")

    if not args.upload_host or not args.upload_dest_filename:
        logger.warning(
            "Upload via SCP improperly confgured. Snapshots will not be uploaded")

    # define the magnetic door sensor connected to pin 14
    door_sensor = Button(14)

    # define the cancel momentary push button connected to pin 27
    cancel_button = Button(27)

    # create the camera controller instance
    cam_control = GarageCameraController()
    # configure output dirs
    cam_control.snapshot_dir = args.snapshot_dir
    cam_control.video_dir = args.video_dir
    cam_control.upload_host = args.upload_host
    cam_control.upload_host_username = args.upload_host_username
    cam_control.upload_dest_filename = args.upload_dest_filename

    # hook door sensor press/released callbacks to the camera controller
    door_sensor.when_pressed = lambda: cam_control.door_open()
    door_sensor.when_released = lambda: cam_control.door_closed()

    # hook cancel button pressed callbacks to the camera controller
    cancel_button.when_pressed = lambda: cam_control.cancel_requested()

    # kick off if the door is open when the script is run
    if door_sensor.is_pressed:
        door_sensor.when_pressed()

    # configure periodically taking a picture
    def periodic_take_picture():
        cam_control.take_picture()
    lc = LoopingCall(periodic_take_picture)
    lc.start(60)

    # and kick off the reactor
    reactor.run()

if __name__ == "__main__":
    main()