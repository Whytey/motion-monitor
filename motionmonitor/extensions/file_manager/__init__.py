'''
Created on 11/08/2013

@author: djwhyte
'''

import datetime
import logging
import os
import threading

import motionmonitor.core
import extensions.mysql_db_server.__init__
from motionmonitor.const import (
    EVENT_JOB,
    EVENT_MANAGEMENT_ACTIVITY
)


def get_extension(mm):
    return [Auditor(mm), Sweeper(mm)]


def delete_path(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)


def delete_dir_if_empty(path, delParents=False):
    if os.path.exists(path) and os.path.isdir(path) and not os.listdir(path):
        os.rmdir(path)
        if delParents:
            delete_dir_if_empty(os.path.split(path)[0], delParents)


class AuditorThread(threading.Thread):

    def __init__(self, mm):
        threading.Thread.__init__(self)
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm

        # Extract the following from the config
        self.target_dir = self.mm.config.TARGET_DIR

        # Extract the following from the config
        self.snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'

        # Extract the following from the config
        self.motion_filename = 'motion/camera%t/%Y%m%d/%C/%Y%m%d-%H%M%S-%q.jpg'
        self.__logger.info("Initialised")

    @staticmethod
    def __split_all(path):
        allparts = []
        while 1:
            parts = os.path.split(path)
            if parts[0] == path:  # sentinel for absolute paths
                allparts.insert(0, parts[0])
                break
            elif parts[1] == path:  # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts

    def __get_camera_from_filepath(self, filepath):
        camera_folder = self.__split_all(filepath)[4]
        camera = camera_folder.replace("camera", "")
        return camera

    def __get_timestamp_from_snapshot_filepath(self, filepath):
        year = self.__split_all(filepath)[5]
        month = self.__split_all(filepath)[6]
        day = self.__split_all(filepath)[7]
        hours = self.__split_all(filepath)[8]
        mins = self.__split_all(filepath)[9]
        secs_file = self.__split_all(filepath)[10]
        secs = secs_file.replace("-snapshot.jpg", "")
        return "%s%s%s%s%s%s" % (year, month, day, hours, mins, secs)

    def __get_timestamp_from_motion_filepath(self, filepath):
        filename = self.__split_all(filepath)[7]
        date = filename.split("-")[0]
        time = filename.split("-")[1]
        return "{}{}".format(date, time)

    def __get_starttime_from_motion_event(self, event):
        return event.split("-")[0]

    def __get_event_from_motion_filepath(self, filepath):
        return self.__split_all(filepath)[6]

    def __get_frame_from_motion_filepath(self, filepath):
        filename = self.__split_all(filepath)[7]
        filename = filename.replace(".jpg", "")
        frame = filename.split("-")[2]
        return frame

    def __audit_snapshot_frames(self):
        try:
            insertedFiles = []
            for root, dirs, files in os.walk(self.target_dir, topdown=True):

                # Hack! Only worry about snapshot files.
                if not root.startswith('/data/motion/snapshots'): continue

                delete_dir_if_empty(root, True)

                try:
                    for filename in files:
                        filepath = os.path.join(root, filename)

                        row = (self.__get_camera_from_filepath(filepath),
                               self.__get_timestamp_from_snapshot_filepath(filepath),
                               0,
                               filepath)

                        self.__logger.debug("Inserting the following snapshot file: %s" % str(row))
                        insertedFiles.append(row)

                        if len(insertedFiles) > 50:
                            self.__logger.debug("Inserting DB entries: %s" % insertedFiles)
                            self.__sqlwriter.insert_snapshot_frames(insertedFiles)
                            insertedFiles = []
                except Exception as e:
                    self.__logger.exception(e)

            # Insert the file into the DB
            self.__logger.debug("Inserting remaining DB entries: %s" % insertedFiles)
            self.__sqlwriter.insert_snapshot_frames(insertedFiles)
        except Exception as e:
            self.__logger.exception(e)
            raise

    def __audit_motion_frames(self):
        try:
            insertedFiles = []
            for root, dirs, files in os.walk(self.target_dir, topdown=True):

                # Hack! Only worry about motion files.
                if not root.startswith('/data/motion/motion'): continue

                delete_dir_if_empty(root, True)

                try:
                    for filename in files:
                        filepath = os.path.join(root, filename)

                        eventId = self.__get_event_from_motion_filepath(filepath)
                        cameraId = self.__get_camera_from_filepath(filepath)
                        timestamp = self.__get_timestamp_from_motion_filepath(filepath)
                        frame = self.__get_frame_from_motion_filepath(filepath)

                        # Some validation
                        try:
                            if len(self.__split_all(filepath)) != 8:
                                raise ValueError("Not right number of parts in filepath: {}".format(filepath))
                            if int(frame) < 0:
                                raise ValueError("Frame isn't positive integer: {}".format(frame))
                            datetime.datetime.strptime(timestamp, "%Y%m%d%H%M%S")
                        except ValueError as e:
                            self.__logger.exception(e)
                            self.__logger.warning("Invalid frame, should delete it and skipping {}".format(filename))
                            # delete_path(filename)
                            # delete_dir_if_empty(root, True)
                            continue

                        row = (eventId, cameraId, timestamp, frame, 0, filepath)

                        self.__logger.debug("Inserting the following motion file: %s" % str(row))
                        insertedFiles.append(row)

                        if len(insertedFiles) > 50:
                            self.__logger.debug("Inserting DB entries: %s" % insertedFiles)
                            self.__sqlwriter.insert_motion_frames(insertedFiles)
                            insertedFiles = []

                    if not dirs:
                        # This is a lowest branch, we can work out the motion_event entry
                        starttime = self.__get_starttime_from_motion_event(eventId)
                        row = (eventId, cameraId, starttime)
                        self.__sqlwriter.insert_motion_events([row])
                except Exception as e:
                    self.__logger.exception(e)

            # Insert the file into the DB
            self.__logger.debug("Inserting remaining DB entries: %s" % insertedFiles)
            self.__sqlwriter.insert_motion_frames(insertedFiles)
        except Exception as e:
            self.__logger.exception(e)
            raise

    def run(self):
        self.__sqlwriter = extensions.mysql_db_server.__init__.SQLWriter(self.mm)
        self.__logger.info("Auditing the motion frames")
        self.__audit_motion_frames()
        self.__logger.info("Motion auditing finished")
        self.__logger.info("Auditing the snapshot frames")
        self.__audit_snapshot_frames()
        self.__logger.info("Snapshot auditing finished")
        self.__sqlwriter.close()


class Auditor():

    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.mm = mm
        self.__logger.info("Initialised")
        self.__thread = None

    async def start_extension(self):
        self.mm.bus.listen(EVENT_MANAGEMENT_ACTIVITY, self.audit)
        self.__logger.info("Started")

    def audit(self, event):
        msg = event.data
        if not msg["type"] in ["audit"]: return

        if not self.__thread or not self.__thread.isAlive():
            # Create a thread and start it
            self.__logger.info("Creating a new AuditorThread and starting it")
            self.__thread = AuditorThread(self.mm)
            self.__thread.start()
        else:
            self.__logger.warning("AuditorThread is already running")


class SweeperThread(threading.Thread):

    def __init__(self, mm):
        threading.Thread.__init__(self)
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        self.__sqlreader = extensions.mysql_db_server.__init__.SQLReader(self.mm)

        self.__job = motionmonitor.core.Job("Sweeper")

        # Extract the following from the config
        self.target_dir = self.mm.config.TARGET_DIR

        self.__logger.info("Initialised")

    def __sweep_snapshot_frames(self):

        try:
            stale_files = []
            stale_files.extend(self.__sqlreader.get_stale_snapshot_frames())

            self.__logger.info("Have %s snapshot files to delete" % len(stale_files))

            # Get the filepath from the returned rowset tuple
            deletedFiles = []
            deletedPaths = set()
            for (cameraId, timestamp, frame, filename) in stale_files:
                if os.path.exists(filename):
                    self.__logger.debug("Deleting stale file: %s" % filename)
                    delete_path(filename)
                    deletedFiles.append((cameraId, timestamp, frame))
                    deletedPaths.add(os.path.dirname(filename))

                if len(deletedFiles) > 50:
                    self.__logger.debug("Deleting stale DB entries: %s" % deletedFiles)
                    self.__sqlreader.delete_snapshot_frame(deletedFiles)
                    deletedFiles = []

            # Cleanup, in case these were missed in the loop
            self.__logger.debug("Deleting remaining stale DB entries: %s" % deletedFiles)
            self.__sqlreader.delete_snapshot_frame(deletedFiles)

            self.__logger.debug("Deleting empty paths now")
            for path in deletedPaths:
                delete_dir_if_empty(path, True)

        except Exception as e:
            self.__logger.exception(e)
            raise

    def __sweep_motion_frames(self):
        try:
            stale_files = []
            stale_files.extend(self.__sqlreader.get_stale_motion_frames())

            self.__logger.info("Have %s motion files to delete" % len(stale_files))

            # Get the filepath from the returned rowset tuple
            deletedFiles = []
            deletedPaths = set()
            for (eventId, cameraId, timestamp, frame, filename) in stale_files:
                if os.path.exists(filename):
                    self.__logger.debug("Deleting stale file: %s" % filename)
                    delete_path(filename)
                    deletedFiles.append((eventId, cameraId, timestamp, frame))
                    deletedPaths.add(os.path.dirname(filename))

                if len(deletedFiles) > 50:
                    self.__logger.debug("Deleting stale DB entries: %s" % deletedFiles)
                    self.__sqlreader.delete_motion_frame(deletedFiles)
                    deletedFiles = []

            # Cleanup, in case these were missed in the loop
            self.__logger.debug("Deleting remaining stale DB entries: %s" % deletedFiles)
            self.__sqlreader.delete_motion_frame(deletedFiles)

            self.__logger.debug("Deleting empty paths now")
            for path in deletedPaths:
                delete_dir_if_empty(path, True)

        except Exception as e:
            self.__logger.exception(e)
            raise

    def run(self):
        self.__job.start()
        self.__job.update_status(1, "Sweeping motion frames")
        self.mm.bus.fire(EVENT_JOB, self.__job)
        self.__logger.info("Sweeping the motion frames")
        self.__sweep_motion_frames()
        self.__logger.info("Motion sweeping finished")
        self.__job.update_status(50, "Sweeping snapshot frames")
        self.mm.bus.fire(EVENT_JOB, self.__job)
        self.__logger.info("Sweeping the snapshot frames")
        self.__sweep_snapshot_frames()
        self.__logger.info("Snapshot sweeping finished")
        self.__job.update_status(100, "Sweeping finished!")
        self.mm.bus.fire(EVENT_JOB, self.__job)


class Sweeper():

    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.mm = mm
        self.__logger.info("Initialised")
        self.__thread = None

    async def start_extension(self):
        self.mm.bus.listen(EVENT_MANAGEMENT_ACTIVITY, self.sweep)
        self.__logger.info("Started")

    def sweep(self, event):
        msg = event.data
        if not msg["type"] in ["sweep"]: return

        if not self.__thread or not self.__thread.isAlive():
            # Create a thread and start it
            self.__logger.info("Creating a new SweeperThread and starting it")
            self.__thread = SweeperThread(self.mm)
            self.__thread.start()
        else:
            self.__logger.warning("SweeperThread is already running")
