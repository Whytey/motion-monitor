'''
Created on 11/08/2013

@author: djwhyte
'''

import logging
import monitor.sqlexchanger
import os
import threading

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
    
    def __init__(self, sqlwriter):
        threading.Thread.__init__(self)
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        
        self.__sqlwriter = sqlwriter
        
        # Extract the following from the config
        self.target_dir = '/data/motion'
    
        # Extract the following from the config
        self.snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'
        

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
    
    def __get_timestamp_from_filepath(self, filepath):
        year = self.__split_all(filepath)[5]
        month = self.__split_all(filepath)[6]
        day = self.__split_all(filepath)[7]
        hours = self.__split_all(filepath)[8]
        mins = self.__split_all(filepath)[9]
        secs_file = self.__split_all(filepath)[10]
        secs = secs_file.replace("-snapshot.jpg", "")
        return "%s%s%s%s%s%s" % (year, month, day, hours, mins, secs)

    def run(self):
        try:
            insertedFiles = []
            for root, dirs, files in os.walk(self.target_dir, topdown=True):
                
                # Hack! Only worry about snapshot files.
                if not root.startswith('/data/motion/snapshots'): continue
                
                delete_dir_if_empty(root, True)
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    row = (self.__get_camera_from_filepath(filepath),
                           filepath,
                           0,
                           0,
                           2,
                           self.__get_timestamp_from_filepath(filepath),
                           "")
                    
                    self.__logger.debug("Inserting the following snapshot file: %s" % str(row))
                    insertedFiles.append(row)
                    
                    if len(insertedFiles) > 50:
                        self.__logger.debug("Inserting DB entries: %s" % insertedFiles)
                        self.__sqlwriter.insert_files_into_db(insertedFiles)
                        insertedFiles = []
                    
            # Insert the file into the DB
            self.__logger.debug("Inserting remaining DB entries: %s" % insertedFiles)
            self.__sqlwriter.insert_files_into_db(insertedFiles)
        except Exception as e:
            self.__logger.exception(e)
            raise

class Auditor():
    
    def __init__(self):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__thread = None


    def insert_orphaned_snapshots(self, object, msg):
        
        if not msg["type"] in ["audit"] : return
        
        if not self.__thread or not self.__thread.isAlive():
            # Create a thread and start it
            self.__logger.info("Creating a new AuditorThread and starting it")
            sqlwriter = monitor.sqlexchanger.SQLWriter(monitor.sqlexchanger.DB().getConnection())
            self.__thread = AuditorThread(sqlwriter)
            self.__thread.start()
        else:
            self.__logger.warning("AuditorThread is already running")
            
class SweeperThread(threading.Thread):
    
    def __init__(self, sqlwriter):
        threading.Thread.__init__(self)
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        
        self.__sqlwriter = sqlwriter

        # Extract the following from the config
        self.target_dir = '/data/motion'

        
    def run(self):
        try:
            stale_files = []
            stale_files.extend(self.__sqlwriter.get_stale_snapshots())
            stale_files.extend(self.__sqlwriter.get_stale_motion())
            
            self.__logger.info("Have %s files to delete" % len(stale_files))

            # Get the filepath from the returned rowset tuple
            deletedFiles = []
            deletedPaths = set()
            for (filepath,) in stale_files:
                if os.path.exists(filepath):
                    self.__logger.debug("Deleting stale file: %s" % filepath)
                    delete_path(filepath)
                    deletedFiles.append(filepath)
                    deletedPaths.add(os.path.dirname(filepath))
                    
                if len(deletedFiles) > 50:
                    self.__logger.debug("Deleting stale DB entries: %s" % deletedFiles)
                    self.__sqlwriter.remove_files_from_db(deletedFiles)
                    deletedFiles = []
                    
            # Cleanup, in case these were missed in the loop
            self.__logger.debug("Deleting remaining stale DB entries: %s" % deletedFiles)
            self.__sqlwriter.remove_files_from_db(deletedFiles)
            
            for path in deletedPaths:
                self.__logger.debug("Deleting empty paths now")
                delete_dir_if_empty(path, True)

        except Exception as e:
            self.__logger.exception(e)
            raise        
    
class Sweeper():
    
    def __init__(self):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.info("Initialised")
        self.__thread = None

    def sweep(self, object, msg):
        
        if not msg["type"] in ["sweep"] : return
        
        if not self.__thread or not self.__thread.isAlive():
            # Create a thread and start it
            self.__logger.info("Creating a new SweeperThread and starting it")
            sqlwriter = monitor.sqlexchanger.SQLWriter(monitor.sqlexchanger.DB().getConnection())
            self.__thread = SweeperThread(sqlwriter)
            self.__thread.start()
        else:
            self.__logger.warning("SweeperThread is already running")

