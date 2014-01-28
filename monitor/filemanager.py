'''
Created on 11/08/2013

@author: djwhyte
'''

from datetime import datetime, timedelta
import logging
import monitor.sqlexchanger
import os
import re
import sys
import time

class Statistics():
  def __init__(self):
              
    self.__logger = logging.getLogger(__name__)

    self.started = datetime.now()
    self.deleted_dirs = 0
    self.deleted_files = 0

  def start_regex_generation(self):
    self.start_regex_gen = datetime.now()

  def finish_regex_generation(self):
    self.finish_regex_gen = datetime.now()

  def start_sweeping(self):
    self.start_sweep = datetime.now()

  def finish_sweeping(self):
    self.finish_sweep = datetime.now()

  def file_deleted(self):
    self.deleted_files += 1

  def dir_deleted(self):
    self.deleted_dirs += 1

  def log_stats(self):
    self.__logger.info("Script started: {0:%Y-%m-%d %H:%M:%S}".format(self.started))
    self.__logger.info("Regex generation took: {0}".format(self.finish_regex_gen - self.start_regex_gen))
    self.__logger.info("Sweeping took: {0}".format(self.finish_sweep - self.start_sweep))
    self.__logger.info("Cleaned up {0:02d} files and {1:02d} directories".format(self.deleted_files, self.deleted_dirs))

class TimelapseConfig():
  def __init__(self):
              
    self.__logger = logging.getLogger(__name__)

    # From the config
    self.target_dir = '/data/motion'

    self.timelapse_filename = 'timelapse/camera%t/%Y/%m/%d-timelapse'

    self.keep_days = 7    

  # build up a list of files that we can keep.
  # iterate through everything and if it isn't 
  # in the keep list we delete it.
  def create_regexes(self):
    regexes = []
    now = datetime.now()

    # Keep days (jpegs)
    for day in range(self.keep_days):
      date = now - timedelta(days=day)
      data_path = os.path.join(self.target_dir, self.timelapse_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))
      data_path = data_path.replace(re.escape("%d"), "{0:02d}".format(date.day))
      data_path = data_path.replace(re.escape("%v"), "[0-9]+")
      data_path = data_path.replace(re.escape("%H"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%M"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%S"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%q"), "[0-9]+")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))

    return regexes 
      
      
class MotionDetectConfig():
  def __init__(self):
                    
    self.__logger = logging.getLogger(__name__)

    # From the config
    self.target_dir = '/data/motion'

    self.jpeg_filename = 'motion/camera%t/%Y%m%d/%v/%Y%m%d-%H%M%S-%q'

    self.movie_filename = 'motion/camera%t/%Y%m%d/%v/%Y%m%d-%H%M%S'

    self.keep_days = 14

  # build up a list of files that we can keep.
  # iterate through everything and if it isn't 
  # in the keep list we delete it.
  def create_regexes(self):
    regexes = []
    now = datetime.now()

    # Keep days (jpegs)
    for day in range(self.keep_days):
      date = now - timedelta(days=day)
      data_path = os.path.join(self.target_dir, self.jpeg_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))
      data_path = data_path.replace(re.escape("%d"), "{0:02d}".format(date.day))
      data_path = data_path.replace(re.escape("%v"), "[0-9]+")
      data_path = data_path.replace(re.escape("%H"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%M"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%S"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%q"), "[0-9]+")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))

    # Keep days (movie)
    for day in range(self.keep_days):
      date = now - timedelta(days=day)
      data_path = os.path.join(self.target_dir, self.movie_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))
      data_path = data_path.replace(re.escape("%d"), "{0:02d}".format(date.day))
      data_path = data_path.replace(re.escape("%v"), "[0-9]+")
      data_path = data_path.replace(re.escape("%H"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%M"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%S"), "[0-9]{2}")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))
        
    return regexes


class SnapshotConfig():

  def __init__(self):
                    
    self.__logger = logging.getLogger(__name__)

    # Extract the following from the config
    self.target_dir = '/data/motion/'
    # Extract the following from the config
    self.snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'

    # This is specific config for this script.
    self.keep_days = 7
    self.keep_weeks = 4
    self.keep_months = 3
    self.keep_years = 10

  # build up a list of files that we can keep.
  # iterate through everything and if it isn't 
  # in the keep list we delete it.
  def create_regexes(self):
    regexes = []
    now = datetime.now()

    # Keep days
    for day in range(self.keep_days):
      date = now - timedelta(days=day)
      data_path = os.path.join(self.target_dir, self.snapshot_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))
      data_path = data_path.replace(re.escape("%d"), "{0:02d}".format(date.day))
      data_path = data_path.replace(re.escape("%H"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%M"), "[0-9]{2}")
      data_path = data_path.replace(re.escape("%S"), "[0-9]{2}")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))
  
    # Keep weeks
    for day in range(self.keep_weeks * 7):
      date = now - timedelta(days=day)
      data_path = os.path.join(self.target_dir, self.snapshot_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))    
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))    
      data_path = data_path.replace(re.escape("%d"), "{0:02d}".format(date.day))    
      data_path = data_path.replace(re.escape("%H"), "(0[0-9]|1[0-9]|2[123])")
      data_path = data_path.replace(re.escape("%M"), "00")
      data_path = data_path.replace(re.escape("%S"), "00")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))

    # Keep months
    # Change the range so that it goes back three months in timedelta
    for month in range(self.keep_months):
      date = now - timedelta(days=month * 365 / 12)
      data_path = os.path.join(self.target_dir, self.snapshot_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))    
      data_path = data_path.replace(re.escape("%m"), "{0:02d}".format(date.month))    
      data_path = data_path.replace(re.escape("%d"), "(0[1-9]|1[0-9]|2[0-9]|3[01])")    
      data_path = data_path.replace(re.escape("%H"), "(06|12|18)")
      data_path = data_path.replace(re.escape("%M"), "00")
      data_path = data_path.replace(re.escape("%S"), "00")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))
    
    # Keep years
    for year in range(self.keep_years):
      date = now - timedelta(days=year * 365.24)
      data_path = os.path.join(self.target_dir, self.snapshot_filename)
      data_path = re.escape(data_path)
      data_path = data_path.replace(re.escape("%t"), "[1234]") 
      data_path = data_path.replace(re.escape("%Y"), "{0:02d}".format(date.year))    
      data_path = data_path.replace(re.escape("%m"), "(0[1-9]|1[012])")    
      data_path = data_path.replace(re.escape("%d"), "(0[1-9]|1[0-9]|2[0-9]|3[01])")    
      data_path = data_path.replace(re.escape("%H"), "12")
      data_path = data_path.replace(re.escape("%M"), "00")
      data_path = data_path.replace(re.escape("%S"), "00")
      regex = "^%s" % data_path
      self.__logger.debug(regex)
      regexes.append(re.compile(regex))

    return regexes

class Auditor():
    
    def __init__(self, sqlwriter):
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
            elif parts[1] == path: # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts
        
    def __get_camera_from_filepath(self, filepath):
        camera_folder = self.__split_all(filepath)[3]
        camera = camera_folder.replace("camera", "")
        return camera
    
    def __get_timestamp_from_filepath(self, filepath):
        year = self.__split_all(filepath)[4]
        month = self.__split_all(filepath)[5]
        day = self.__split_all(filepath)[6]
        hours = self.__split_all(filepath)[7]
        mins = self.__split_all(filepath)[8]
        secs_file = self.__split_all(filepath)[9]
        secs = secs_file.replace("-snapshot.jpg", "")
        return "%s%s%s-%s:%s:%s" % (year, month, day, hours, mins, secs)

    def insert_orphaned_snapshots(self, object, msg):
        
        if not msg["type"] in ["audit"] : return
        
        for root, dirs, files in os.walk(self.target_dir, topdown=False):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                row = {"camera": self.__get_camera_from_filepath(filepath),
                      "file": filepath,
                      "frame": 0,
                      "score": 0,
                      "filetype": 2,
                      "timestamp": self.__get_timestamp_from_filepath(filepath),
                      "event": ""}
                
                self.__logger.debug("Inserting the following snapshot file: %s" % row)
                
                # Insert the file into the DB
                self.__sqlwriter.insert_file_into_db(row)
            
            
class Sweeper():
    
    def __init__(self):
      self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
      self.__logger.info("Initialised")



    def __delete_path(self, path, test):
      if test:
        return
      if os.path.isdir(path):
        os.rmdir(path)
      else:
        os.remove(path)
    
    
    def sweep(self, object, msg):
        
      if not msg["type"] in ["sweep"] : return
      
      stats = Statistics()
    
      try:
        stats.start_regex_generation()
        
        time.sleep(10)
    
        regexes = []
        regexes.extend(TimelapseConfig().create_regexes())
        regexes.extend(MotionDetectConfig().create_regexes())
        regexes.extend(SnapshotConfig().create_regexes())
    
        stats.finish_regex_generation()
    
        stats.start_sweeping()
    
        test = False
        conf = TimelapseConfig()
    
        for root, dirs, files in os.walk(conf.target_dir, topdown=False):
          for file in files:
            found = False
            filepath = os.path.join(root, file)
            for regex in regexes:
              if regex.match(filepath):
                self.__logger.debug("found: %s" % filepath)
                found = True
                break
            if not found:
              self.__logger.debug("removing: %s" % filepath)
              stats.file_deleted()
              self.__delete_path(filepath, test)
          for dir in dirs:
            dirpath = os.path.join(root, dir)
            if not os.listdir(dirpath):
              # dir is empty
              self.__logger.debug("removing: %s" % dirpath)
              stats.dir_deleted()
              self.__delete_path(dirpath, test)
    
    
      except KeyboardInterrupt:
        pass
    
      stats.finish_sweeping()
      stats.log_stats()
