import logging
import os
import socket
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
from motionmonitor import config
import json

MOTION_TYPE = "1"
SNAPSHOT_TYPE = "2"

EVENT_ID = "0"

global config
logger = logging.getLogger('motionmonitor')
logger.setLevel(logging.getLevelName("DEBUG"))
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.debug("Logger configured")


def _determine_filename(filepath, camera_id, timestamp=datetime.now(), event_id="0", frame="0"):
    return config["GENERAL"]["TARGET_DIR"] + filepath\
        .replace("%t", str(camera_id))\
        .replace("%Y", timestamp.strftime("%Y"))\
        .replace("%m", timestamp.strftime("%m"))\
        .replace("%d", timestamp.strftime("%d"))\
        .replace("%H",timestamp.strftime("%H"))\
        .replace("%M", timestamp.strftime("%M"))\
        .replace("%S", timestamp.strftime("%S"))\
        .replace("%C", event_id) \
        .replace("%q", frame.zfill(2)) + ".jpg"


def _create_image_file(target_filename):
    img = Image.new('RGB', (320, 240), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((18, 18), target_filename, fill=(255, 255, 0))
    print(target_filename)
    target_dir = os.path.dirname(target_filename)

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    img.save(target_filename)


def _send_socket_msg(camera_id, picture_type, timestamp, filename, event_id="0"):
    UDP_IP = config["SOCKET_SERVER"]["ADDRESS"]
    UDP_PORT = int(config["SOCKET_SERVER"]["PORT"])
    message = {"type": "picture_save",
               "camera": camera_id,
               "file": filename,
               "filetype": picture_type,
               "score": "0",
               "event": event_id,
               "timestamp": timestamp.strftime("%Y%m%d%H%M%S"),
               "frame": "0"}

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.sendto(json.dumps(message).encode(), (UDP_IP, UDP_PORT))


def create_snapshot_frame(camera_id="1"):
    timestamp = datetime.now()
    filename = _determine_filename(config["GENERAL"]["SNAPSHOT_FILENAME"], camera_id, timestamp)
    _create_image_file(filename)
    _send_socket_msg(camera_id, SNAPSHOT_TYPE, timestamp, filename)

def create_motion_frame(camera_id="1"):
    timestamp = datetime.now()
    event_id = timestamp.strftime("%Y%m%d-%H%M%S")
    filename = _determine_filename(config["GENERAL"]["MOTION_FILENAME"], camera_id, timestamp, event_id)
    _create_image_file(filename)
    _send_socket_msg(camera_id, MOTION_TYPE, timestamp, filename, event_id)

if __name__ == '__main__':

    config = config.ConfigReader().read_config("motion-monitor.ini.test", False)

    create_snapshot_frame("1")
    create_snapshot_frame("2")
    create_snapshot_frame("3")
    create_motion_frame("1")
    create_motion_frame("2")
