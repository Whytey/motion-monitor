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

    def insert_files_into_db(self, files):
        self.__logger.debug("Inserting data to the DB: %s" % files)
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ifgnore any duplicates (as determined by the filename)
            query = "insert ignore into security (camera, filename, frame, score, file_type, time_stamp, text_event) values (%s, %s, %s, %s, %s, %s, %s)"
            cursor.executemany(query, files)
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
                query =  "delete from security where filename in (%s)"
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
                                from security
                                where
                                    file_type = 2 and
                                    ((time_stamp < subdate(now(), interval 7 day) and minute(time_stamp) != 0) or
                                    (time_stamp < subdate(now(), interval 4 week) and (hour(time_stamp) not in (6, 12, 18) or minute(time_stamp) != 0)) or
                                    (time_stamp < subdate(now(), interval 3 month) and (hour(time_stamp) != 12 or minute(time_stamp) != 0)))""")
            
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
            
            # Select just the snapshot filenames that are stale
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

                
    def handle_motion_event(self, object, msg):
        try:
            self.__logger.debug("Handling a message: %s" % msg)
            if msg["type"] not in ["picture_save", "movie_start", "movie_end"]:
                # Not a message we log to the DB
                return True
            
            files = [(msg['camera'],
                      msg['file'], 
                      msg['frame'],
                      msg['score'],
                      msg['filetype'],
                      msg['timestamp'],
                      msg['event'])]
            
            self.insert_files_into_db(files)

        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
