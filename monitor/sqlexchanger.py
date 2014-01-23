'''
Created on 22/01/2014

@author: djwhyte
'''
import logging
import MySQLdb

class SQLWriter():
    
    __DB_NAME = "motion"
    __DB_HOST = "localhost"
    __DB_USER = "motion"
    __DB_PASSWORD = "motion"

    
    def __init__(self):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__db = MySQLdb.connect(host=self.__DB_HOST, db=self.__DB_NAME, user=self.__DB_USER, passwd=self.__DB_PASSWORD)
        self.__logger.info("Initialised")

        
    def handle_motion_event(self, object, msg):
        try:
            self.__logger.debug("Handling a message: %s" % msg)
            if msg["type"] not in ["picture_save"]:
                # Not a message we log to the DB
                return True
            
            cursor = self.__db.cursor()
            
            cursor.execute("""insert into security (camera, filename, frame, score, file_type, time_stamp, text_event) values(%s, %s, %s, %s, %s, %s, %s)""", 
                           (msg['camera'], 
                            msg['file'], 
                            msg['frame'],
                            msg['score'],
                            msg['filetype'],
                            msg['timestamp'],
                            msg['event']))
            self.__db.commit()
        except Exception as e:
            self.__logger.exception(e)
            self.__db.rollback()
            raise
        return True