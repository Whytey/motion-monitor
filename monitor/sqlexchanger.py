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

class SQLReader():
    
    def __init__(self, connection):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__connection = connection
        
    def get_stale_files(self):
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
            stale_files = cursor.fetchall()
            return stale_files
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise

class SQLWriter():
    
    def __init__(self, connection):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__connection = connection

    def insert_file_into_db(self, msg):
        try:
            cursor = self.__connection.cursor()
            
            # Insert the data to the DB.  Ifgnore any duplicates (as determined by the filename)
            cursor.execute("""insert ignore into security (camera, filename, frame, score, file_type, time_stamp, text_event) values(%s, %s, %s, %s, %s, %s, %s)""", 
                           (msg['camera'], 
                            msg['file'], 
                            msg['frame'],
                            msg['score'],
                            msg['filetype'],
                            msg['timestamp'],
                            msg['event']))
            self.__connection.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__connection.rollback()
            raise
                
    def handle_motion_event(self, object, msg):
        self.__logger.debug("Handling a message: %s" % msg)
        if msg["type"] not in ["picture_save"]:
            # Not a message we log to the DB
            return True
        
        self.insert_file_into_db(msg)

        return True