from datetime import datetime, timedelta
import logging
import logging.handlers
import os
import re
import sys


logger = logging.getLogger('motion-manager')
logger.setLevel(logging.DEBUG)

# Determine the path to the log file.
installed_log_path = os.path.join(os.sep, 'var','log','motion-manager')
log_filename = 'sweeper.log'
if os.path.exists(installed_log_path):
    logger_path = os.path.join(installed_log_path, log_filename)
else:  
    non_installed_log_path = os.path.join(os.sep, 'tmp', 'motion-manager')
    if not os.path.exists(non_installed_log_path):
        os.makedirs(non_installed_log_path)
    logger_path = os.path.join(non_installed_log_path, log_filename)

# Add the log message handler to the logger
file_handler = logging.handlers.RotatingFileHandler(
               logger_path, backupCount=7)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

file_handler.doRollover()

class Statistics():
  def __init__(self):
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
    logger.info("Script started: {0:%Y-%m-%d %H:%M:%S}".format(self.started))
    logger.info("Regex generation took: {0}".format(self.finish_regex_gen - self.start_regex_gen))
    logger.info("Sweeping took: {0}".format(self.finish_sweep - self.start_sweep))
    logger.info("Cleaned up {0:02d} files and {1:02d} directories".format(self.deleted_files, self.deleted_dirs))

class TimelapseConfig():
  def __init__(self):
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
      logger.debug(regex)
      regexes.append(re.compile(regex))

    return regexes 
      
      
class MotionDetectConfig():
  def __init__(self):
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
      logger.debug(regex)
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
      logger.debug(regex)
      regexes.append(re.compile(regex))
        
    return regexes


class SnapshotConfig():

  def __init__(self):
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
      logger.debug(regex)
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
      logger.debug(regex)
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
      logger.debug(regex)
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
      logger.debug(regex)
      regexes.append(re.compile(regex))

    return regexes

def delete_path(path, test):
  if test:
    return
  if os.path.isdir(path):
    os.rmdir(path)
  else:
    os.remove(path)


def main():
  stats = Statistics()

  try:
    stats.start_regex_generation()

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
            logger.debug("found: %s" % filepath)
            found = True
            break
        if not found:
          logger.debug("removing: %s" % filepath)
          stats.file_deleted()
          delete_path(filepath, test)
      for dir in dirs:
        dirpath = os.path.join(root, dir)
        if not os.listdir(dirpath):
          # dir is empty
          logger.debug("removing: %s" % dirpath)
          stats.dir_deleted()
          delete_path(dirpath, test)


  except KeyboardInterrupt:
    pass

  stats.finish_sweeping()
  stats.log_stats()

main()
