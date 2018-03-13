'''
Created on 22/01/2014

@author: djwhyte
'''
import logging
import datetime
import MySQLdb


class DB():
    _connection = None
    __DB_SERVER_ADDR = None
    __DB_NAME = None
    __DB_USER = None
    __DB_PASSWORD = None

    def __init__(self, config):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        DB.__DB_SERVER_ADDR = config.DB_SERVER_ADDR
        DB.__DB_NAME = config.DB_NAME
        DB.__DB_USER = config.DB_USER
        DB.__DB_PASSWORD = config.DB_PASSWORD

    @staticmethod
    def get_connection():
        if DB._connection is None:
            DB._connection = MySQLdb.connect(host=DB.__DB_SERVER_ADDR, db=DB.__DB_NAME, user=DB.__DB_USER,
                                             passwd=DB.__DB_PASSWORD)
        return DB._connection



class SQLWriter():

    def __init__(self, connection):

        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__connection = connection

    def __run_query(self, query, params=None):
        try:
            cursor = self.__connection.cursor()
        except MySQLdb.OperationalError as e:
            self.__logger.exception("Lost connection to the DB, reconnecting", e)
            self.__connection = DB.get_connection()
            cursor = self.__connection.cursor()

        self.__logger.debug("About to run query: %s" % query)

        try:
            if params:
                cursor.executemany(query, params)
            else:
                cursor.execute(query)
            self.__connection.commit()
            return cursor.fetchall()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

    def insert_snapshot_frames(self, frames):
        self.__logger.debug("Inserting snapshot frame to the DB: %s" % frames)
        # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
        query = """INSERT
                   IGNORE INTO snapshot_frame (camera_id, timestamp, frame, filename)
                   VALUES (%s,
                           %s,
                           %s,
                           %s)"""

        self.__run_query(query, frames)

    def insert_motion_frames(self, frames):
        self.__logger.debug("Inserting motion frame to the DB: %s" % frames)
        # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
        query = """INSERT
                   IGNORE INTO motion_frame (event_id, camera_id, timestamp, frame, score, filename)
                   VALUES (%s,
                           %s,
                           %s,
                           %s,
                           %s,
                           %s)"""
        self.__run_query(query, frames)

    def insert_motion_events(self, events):
        self.__logger.debug("Inserting motion event to the DB: %s" % events)
        # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
        query = """INSERT
                   IGNORE INTO motion_event (event_id, camera_id, start_time)
                   VALUES (%s,
                           %s,
                           %s)"""
        self.__run_query(query, events)

    def delete_snapshot_frame(self, frames):
        self.__logger.debug("Deleting snapshot frames from the DB: %s" % frames)
        # If the list contains frames, remove them from the DB
        if frames:
            query = """DELETE
                       FROM snapshot_frame
                       WHERE camera_id = %s
                       AND timestamp = %s
                       AND frame = %s"""
        self.__run_query(query, frames)

    def delete_motion_frame(self, frames):
        self.__logger.debug("Deleting motion frames from the DB: %s" % frames)
        # If the list contains frames, remove them from the DB
        if frames:
            query = """DELETE
                       FROM motion_frame
                       WHERE event_id = %s
                       AND camera_id = %s
                       AND timestamp = %s
                       AND frame = %s"""
        self.__run_query(query, frames)

    def get_timelapse_snapshot_frames(self, cameraId, startTime, minuteCount=0, hourCount=0, dayCount=0, weekCount=0,
                                      monthCount=0):
        self.__logger.debug("Listing snapshots in the DB for timelapse")
        # Select just the snapshot filenames that are stale
        query = """SELECT camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM snapshot_frame
                   WHERE camera_id = {cameraId}
                     AND {startTime} > subdate(now(), INTERVAL 7 DAY) 
                     AND timestamp >= {startTime}
                     AND timestamp < adddate({startTime}, INTERVAL {minuteCount} MINUTE)
                   UNION
                     ( SELECT camera_id,
                              timestamp,
                              frame,
                              filename
                      FROM snapshot_frame
                      WHERE camera_id = {cameraId}
                        AND {startTime} > subdate(now(), INTERVAL 7 DAY)
                        AND timestamp >= {startTime}
                        AND timestamp < adddate({startTime}, INTERVAL {hourCount} HOUR)
                      GROUP BY date(timestamp),
                               hour(timestamp),
                               minute(timestamp))
                   UNION
                     (SELECT camera_id,
                             timestamp,
                             frame,
                             filename
                      FROM snapshot_frame
                      WHERE camera_id = {cameraId}
                        AND {startTime} > subdate(now(), INTERVAL 4 WEEK)
                        AND timestamp >= {startTime}
                        AND timestamp < adddate({startTime}, INTERVAL {dayCount} DAY)
                      GROUP BY date(timestamp),
                               hour(timestamp))
                   UNION
                     (SELECT camera_id,
                             timestamp,
                             frame,
                             filename
                      FROM snapshot_frame
                      WHERE camera_id = {cameraId}
                        AND {startTime} > subdate(now(), INTERVAL 3 MONTH)
                        AND timestamp >= {startTime}
                        AND timestamp < adddate({startTime}, INTERVAL {weekCount} WEEK)
                        AND hour(timestamp) IN (06,
                                                12,
                                                18)
                      GROUP BY date(timestamp),
                               hour(timestamp))
                   UNION
                     (SELECT camera_id,
                             timestamp,
                             frame,
                             filename
                      FROM snapshot_frame
                      WHERE camera_id = {cameraId}
                        AND timestamp >= {startTime}
                        AND timestamp < adddate({startTime}, INTERVAL {monthCount} MONTH)
                        AND hour(timestamp) = 12
                      GROUP BY date(timestamp),
                               hour(timestamp))""".format(cameraId=cameraId,
                                                          startTime=startTime,
                                                          minuteCount=minuteCount,
                                                          hourCount=hourCount,
                                                          dayCount=dayCount,
                                                          weekCount=weekCount,
                                                          monthCount=monthCount)
        return self.__run_query(query)

    def get_stale_snapshot_frames(self):
        timeNow = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # First create the temporary table
        query = """CREATE
                   TEMPORARY TABLE IF NOT EXISTS retain_frames (INDEX idx_time_camera (timestamp, camera_id))AS
                   SELECT camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM (
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame a
                            WHERE timestamp >= subdate(%s, INTERVAL 7 DAY))
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame b
                            WHERE timestamp < subdate(%s, INTERVAL 7 DAY)
                              AND timestamp >= subdate(%s, INTERVAL 4 WEEK)
                              AND minute(timestamp) = 0
                            GROUP BY camera_id,
                                     date(timestamp),
                                     hour(timestamp),
                                     minute(timestamp))
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame c
                            WHERE timestamp < subdate(%s, INTERVAL 4 WEEK)
                              AND timestamp >= subdate(%s, INTERVAL 3 MONTH)
                              AND hour(timestamp) IN (6,
                                                      12,
                                                      18)
                              AND minute(timestamp) = 0
                            GROUP BY camera_id,
                                     date(timestamp),
                                     hour(timestamp),
                                     minute(timestamp))
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame d
                            WHERE timestamp < subdate(%s, INTERVAL 3 MONTH)
                              AND hour(timestamp) = 12
                              AND minute(timestamp) = 0
                            GROUP BY camera_id,
                                     date(timestamp),
                                     hour(timestamp),
                                     minute(timestamp))) e""" % (timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow)
        self.__run_query(query)

        # Select just the snapshot filenames that are stale
        query = """SELECT camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM snapshot_frame a
                   WHERE timestamp < %s
                     AND NOT EXISTS
                       (SELECT camera_id,
                               timestamp,
                               frame,
                               filename
                        FROM retain_frames b
                        WHERE a.camera_id = b.camera_id
                          AND a.timestamp = b.timestamp
                          AND a.frame = b.frame)""" % timeNow
        return self.__run_query(query)

    def get_stale_motion_frames(self):
        self.__logger.debug("Listing stale motion files in the DB")
        # First, delete the events that are stale
        query = """DELETE
                   FROM motion_event
                   WHERE start_time < subdate(now(), interval 7 DAY)"""
        self.__run_query(query)

        # Select just the motion filenames that are stale
        query = """SELECT event_id,
                          camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM motion_frame
                   WHERE event_id NOT IN
                       (SELECT event_id
                        FROM motion_event)"""
        return self.__run_query(query)

    def get_motion_events(self, fromTimestamp, toTimestamp, cameraIds):
        self.__logger.debug("Listing motion events in the DB")
        # Select just the events within the range of provided parameters
        query = """SELECT event_id,
                          camera_id,
                          start_time
                   FROM motion_event"""
        wheres = []
        if fromTimestamp:
            wheres.append("start_time > %s" % fromTimestamp)
        if toTimestamp:
            wheres.append("start_time < %s" % toTimestamp)
        if cameraIds:
            wheres.append("camera_id IN (%s)" % ','.join(cameraIds))

        if len(wheres) > 0:
            query = query + "\nWHERE " + "\nAND ".join(wheres)

        return self.__run_query(query)

    def get_motion_event_frames(self, eventId, cameraId):
        self.__logger.debug("Listing motion event frames in the DB")
        # Select just the events within the range of provided parameters
        query = """SELECT event_id,
                          camera_id,
                          timestamp,
                          frame,
                          score,
                          filename
                   FROM motion_frame
                   WHERE event_id = '%s'
                     AND camera_id = %s
                   ORDER BY timestamp""" % (eventId, cameraId)
        return self.__run_query(query)

    def get_timelapse(self, fromTimestamp, toTimestamp, interval):
        pass

    def handle_motion_event(self, object, msg):
        try:
            self.__logger.debug("Handling a message: %s" % msg)
            if msg["type"] not in ["picture_save", "event_start", "event_end"]:
                # Not a message we log to the DB
                return True

            if msg["type"] == "picture_save":
                if msg['filetype'] == "1":  # MotionFrame
                    files = [(msg['event'],
                              msg['camera'],
                              msg['timestamp'],
                              msg['frame'],
                              msg['score'],
                              msg['file'])]
                    self.insert_motion_frames(files)

                if msg['filetype'] == "2":  # SnapshotFrame
                    files = [(msg['camera'],
                              msg['timestamp'],
                              msg['frame'],
                              msg['file'])]
                    self.insert_snapshot_frames(files)

            if msg["type"] == "event_start":
                events = [(msg['event'],
                           msg['camera'],
                           msg['timestamp'])]
                self.insert_motion_events(events)

        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
