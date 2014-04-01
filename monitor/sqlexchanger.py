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

    def insert_snapshot_frame(self, files):
        self.__logger.debug("Inserting snapshot frame to the DB: %s" % files)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """insert ignore into snapshot_frame 
                            (camera_id, timestamp, frame, filename) 
                        values 
                            (%s, %s, %s, %s)"""
            cursor.executemany(query, files)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def insert_motion_frame(self, files):
        self.__logger.debug("Inserting motion frame to the DB: %s" % files)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """insert ignore into motion_frame 
                            (event_id, camera_id, timestamp, frame, score, filename) 
                        values 
                            (%s, %s, %s, %s, %s, %s)"""
            cursor.executemany(query, files)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

    def insert_motion_event(self, event):
        self.__logger.debug("Inserting motion event to the DB: %s" % event)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ignore any duplicates (as determined by the filename)
            query = """insert ignore into motion_event 
                            (event_id, camera_id, start_time) 
                        values 
                            (%s, %s, %s)"""
            cursor.executemany(query, event)
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def remove_files_from_db(self, filepaths):
        self.__logger.debug("Deleting files from the DB: %s" % filepaths)
        try:
            cursor = self.__connection.cursor()
            
            # If the list contains filepaths, remove them from the DB
            if filepaths:
                query =  """delete from security 
                                where 
                                    filename in (%s)"""
                self.__logger.debug("Ready to execute: %s" % query)
                cursor.executemany(query, filepaths) 
                self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def get_stale_snapshots(self):
        self.__logger.debug("Listing stale snapshots in the DB")
        try:
            cursor = self.__connection.cursor()
            
            # Select just the snapshot filenames that are stale
            cursor.execute("""select filename
                                from snapshot_frame
                                where
                                    ((timestamp < subdate(now(), interval 7 day) and minute(timestamp) != 0) or
                                    (timestamp < subdate(now(), interval 4 week) and (hour(timestamp) not in (6, 12, 18) or minute(timestamp) != 0)) or
                                    (timestamp < subdate(now(), interval 3 month) and (hour(timestamp) != 12 or minute(timestamp) != 0)))""")
            
            stale_snapshots = cursor.fetchall()
            return stale_snapshots
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
        
    def get_stale_motion(self):
        self.__logger.debug("Listing stale motion files in the DB")
        try:
            cursor = self.__connection.cursor()
            
            # Select just the motion filenames that are stale
            cursor.execute("""select filename
                                from security
                                where
                                    file_type = 1 and
                                    time_stamp < subdate(now(), interval 7 day)""")
            
            stale_motion = cursor.fetchall()
            return stale_motion
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

    def get_events(self, fromTimestamp, toTimestamp, cameraIds):
        self.__logger.debug("Listing motion events in the DB")
        try:
            cursor = self.__connection.cursor()

            # Select just the events within the range of provided parameters
            query = """select event_id, camera_id, start_time 
                        from motion_event"""
            wheres = []
            if fromTimestamp:
                wheres.append("start_time > %s" % fromTimestamp)
            if toTimestamp:
                wheres.append("start_time < %s" % toTimestamp)
            if cameraIds:
                wheres.append("camera_id in (%s)" % ','.join(cameraIds))
                
            if len(wheres) > 0:
                query = query + " where " + " and ".join(wheres)
                
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
                if msg['filetype'] == 1: # MotionFrame
                    files = [(msg['event'],
                              msg['camera'],
                              msg['timestamp'],
                              msg['frame'],
                              msg['score'],
                              msg['file'])] 
                    self.insert_motion_frame(files)
                
                if msg['filetype'] == 2: # SnapshotFrame
                    files = [(msg['camera'],
                              msg['timestamp'],
                              msg['frame'],
                              msg['file'])]
                    self.insert_snapshot_frame(files)

            if msg["type"] == "event_start":
                events = [(msg['event'],
                          msg['camera'],
                          msg['timestamp'])]
                self.insert_motion_event(events)

        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
