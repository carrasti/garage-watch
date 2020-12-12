from io import BytesIO
import os
import logging
import requests

from datetime import datetime

from picamera import PiCamera
from twisted.internet import reactor

from garage_watch import CameraController

from jwcrypto.jwt import JWT
from jwcrypto.jwk import JWK

# logger for the script
logger = logging.getLogger(__name__)


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

    upload_url = ''
    upload_auth_jwk_path = ''
    upload_auth_jwk = None

    pushbullet_secret = None
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
        self.camera.start_recording(filepath, quality=22)
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
                if self.pushbullet_secret:
                    now = datetime.now()
                    requests.post(
                        'https://api.pushbullet.com/v2/pushes',
                        auth=(self.pushbullet_secret, ''),
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
        now = datetime.now()
        try:
            picture_stream = BytesIO()
            # capture the snapshot
            self.camera.annotate_text = '({}) {}'.format(
                self.state, now.strftime('%Y-%m-%d %H:%M')
            )
            
            self.camera.capture(
                picture_stream,
                format='jpeg',
                quality=82,
                use_video_port=(True if self.state == 'record' else False))
            self.camera.annotate_text = ''
        except Exception :
            logger.exception("Error taking snapshot")
        else:
            logger.info("Snapshot taken")
            picture_stream.seek(0)
            return picture_stream

    def save_picture(self, picture_stream):
        try:
            picture_stream.seek(0)
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
            
            with open(filepath, 'wb') as f:
                f.write(picture_stream.read())

            # create a simbolyc link in the directory
            symlink_path = os.path.join(self.snapshot_dir, 'latest_snapshot.jpg')
            if os.path.lexists(symlink_path):
                os.unlink(symlink_path)
            os.symlink(os.path.join(todaydir, filename), symlink_path)
        except Exception:
            logger.exception("Error saving snapshot")
        else:
            logger.info("Snapshot saved to disk")
        finally:
            picture_stream.seek(0)

    def upload_picture(self, picture_stream):
        """
        Upload the file on the given path to the server
        via HTTP post

        Uses class configuration to determine the url and key to sign
        Authorization Bearer token with JWT
        """
        # skip if improperly configured    
        if not self.upload_url or not self.upload_auth_jwk_path:
            return

        if not self.upload_auth_jwk:
            with open(self.upload_auth_jwk_path, 'rb') as f:
                self.upload_auth_jwk = JWK.from_json(f.read())
        
        try:
            picture_stream.seek(0)
            auth_token = JWT(header={'alg': 'EdDSA', 'kid': self.upload_auth_jwk.key_id}, default_claims={'iat':None, 'exp': None})
            auth_token.validity=300
            auth_token.claims={}
            auth_token.make_signed_token(self.upload_auth_jwk)

            auth_header = 'Bearer {}'.format(auth_token.serialize())
            response = requests.post(
                self.upload_url, 
                files={'file': picture_stream},
                headers={
                    'Authorization': auth_header
                }
            )
            if not response.ok:
                logger.error("Error uploading snapshot. Status code {}".format(response.status_code))
            
        except Exception as exc:
            logger.exception("Error uploading snapshot.")
        else:
            # log success
            logger.info("Snapshot uploaded")
        finally:
            picture_stream.seek(0)