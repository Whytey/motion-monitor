'''
Created on 22/01/2014

@author: djwhyte
'''
import logging
import MySQLdb

class DB():
    __DB_NAME = "motion"
    __DB_HOST = "localhost"
    __DB_USER = "motion"
    __DB_PASSWORD = "motion"

    def __init__(self):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        
    def getConnection(self):
        return MySQLdb.connect(host=self.__DB_HOST, db=self.__DB_NAME, user=self.__DB_USER, passwd=self.__DB_PASSWORD)


class SQLWriter():
    
    def __init__(self, connection):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__connection = connection

    def insert_snapshot_frames(self, frames):
        self.__logger.debug("Inserting snapshot frame to the DB: %s" % frames)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """INSERT
                       IGNORE INTO snapshot_frame (camera_id, timestamp, frame, filename)
                       VALUES (%s,
                               %s,
                               %s,
                               %s)"""
            cursor.executemany(query, frames)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def insert_motion_frames(self, frames):
        self.__logger.debug("Inserting motion frame to the DB: %s" % frames)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """INSERT
                       IGNORE INTO motion_frame (event_id, camera_id, timestamp, frame, score, filename)
                       VALUES (%s,
                               %s,
                               %s,
                               %s,
                               %s,
                               %s)"""
            self.__logger.debug("About to run query: %s" % query)
            cursor.executemany(query, frames)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

    def insert_motion_events(self, events):
        self.__logger.debug("Inserting motion event to the DB: %s" % events)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """INSERT
                       IGNORE INTO motion_event (event_id, camera_id, start_time)
                       VALUES (%s,
                               %s,
                               %s)"""
            cursor.executemany(query, events)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def delete_snapshot_frame(self, frames):
        self.__logger.debug("Deleting snapshots from the DB: %s" % frames)
        try:
            cursor = self.__connection.cursor()
            
            # If the list contains frames, remove them from the DB
            if frames:
                query = """DELETE
                           FROM snapshot_frame
                           WHERE camera_id = %s
                           AND TIMESTAMP = %s
                           AND frame = %s"""
                self.__logger.debug("Ready to execute: %s" % query)
                cursor.executemany(query, frames) 
                self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def get_stale_snapshot_frames(self):
        self.__logger.debug("Listing stale snapshots in the DB")
        try:
            cursor = self.__connection.cursor()
            
            # Select just the snapshot filenames that are stale
            query = """SELECT camera_id,
                              timestamp,
                              frame,
                              filename
                       FROM snapshot_frame
                       WHERE ((timestamp < subdate(now(), INTERVAL 7 DAY)
                               AND minute(timestamp) != 0)
                              OR (timestamp < subdate(now(), INTERVAL 4 WEEK)
                                  AND (hour(timestamp) NOT IN (6,
                                                               12,
                                                               18)
                                       OR minute(timestamp) != 0))
                              OR (timestamp < subdate(now(), INTERVAL 3 MONTH)
                                  AND (hour(timestamp) != 12
                                       OR minute(timestamp) != 0)))"""
            self.__logger.debug("About to run query: %s" % query)
            cursor.execute(query)
            
            stale_snapshots = cursor.fetchall()
            return stale_snapshots
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def get_stale_motion_frames(self):
        self.__logger.debug("Listing stale motion files in the DB")
        try:
            cursor = self.__connection.cursor()
            
            # First, delete the events that are stale
            query = """DELETE
                       FROM motion_event
                       WHERE starttime < subdate(now(), interval 7 DAY)"""
            self.__logger.debug("About to run query: %s" % query)
            cursor.execute(query)
            self.__connection.commit()
            
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
            self.__logger.debug("About to run query: %s" % query)
            cursor.execute(query)
            
            stale_motion = cursor.fetchall()
            return stale_motion
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

    def get_motion_events(self, fromTimestamp, toTimestamp, cameraIds):
        self.__logger.debug("Listing motion events in the DB")
        try:
            cursor = self.__connection.cursor()

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
                
            self.__logger.debug("About to run query: %s" % query)
            
            cursor.execute(query)
            
            events = cursor.fetchall()

            return events
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def get_timelapse(self, fromTimestamp, toTimestamp, interval):
        pass
                
    def handle_motion_event(self, object, msg):
        try:
            self.__logger.debug("Handling a message: %s" % msg)
            if msg["type"] not in ["picture_save", "event_start", "event_end"]:
                # Not a message we log to the DB
                return True
            
            if msg["type"] == "picture_save":
                if msg['filetype'] == "1": # MotionFrame
                    files = [(msg['event'],
                              msg['camera'],
                              msg['timestamp'],
                              msg['frame'],
                              msg['score'],
                              msg['file'])] 
                    self.insert_motion_frames(files)
                
                if msg['filetype'] == "2": # SnapshotFrame
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
