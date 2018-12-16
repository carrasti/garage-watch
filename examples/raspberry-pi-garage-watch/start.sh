#!/bin/bash
PYTHONPATH=/home/pi/projects/garage-watch:/home/pi/projects/garage-watch/examples/raspberry-pi-advanced python main.py --snapshot-dir=/media/SNAPSHOTS/garage --video-dir=/media/SNAPSHOTS/garage/recordings --upload-host=webcams.monkeynirvana.com --upload-host-username=webcams --upload-dest-filename=/webapps/webcams/html/garage.jpg
