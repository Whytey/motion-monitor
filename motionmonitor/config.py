import logging
import os
import configparser


class ConfigReader():
    __config_filename = 'motion-monitor.ini'

    def __init__(self):
        self.__logger = logging.getLogger(__name__)
        self.__logger.info("Initialised...")

    def readConfig(self, filename=None, ignore_defaults=False):
        config = configparser.ConfigParser()

        if not ignore_defaults:
            # Attempt to read the defaults, from the possible locations.
            defaultLocations = [os.curdir, "/etc/motion-monitor"]
            for location in defaultLocations:
                try:
                    filepath = os.path.join(location, self.__config_filename + ".default")
                    self.__logger.debug("Attempting to read default config from %s" % filepath)
                    with open(filepath) as source:
                        config.readfp(source)
                        self.__logger.info("Read default config from %s" % filepath)
                        break
                except IOError:
                    self.__logger.error("Error reading default config from %s" % location)

        if filename:
            try:
                filepath = filename
                if os.path.exists(filepath):
                    config.read(filepath)
                    self.__logger.info("Overwrote defaults with config from %s" % filepath)
            except IOError:
                self.__logger.error("Error overwriting config from %s" % filename)
        else:
            # Attempt to overwrite the defaults with user specifics
            overrideLocations = [os.curdir, os.path.expanduser("~/.motion-monitor"), "/etc/motion-monitor"]
            for location in overrideLocations:
                try:
                    filepath = os.path.join(location, self.__config_filename)
                    if os.path.exists(filepath):
                        config.read(filepath)
                        self.__logger.info("Overwrote defaults with config from %s" % filepath)
                        break
                except IOError:
                    self.__logger.error("Error overwriting config from %s" % location)

        self.__logger.debug(config)

        return config