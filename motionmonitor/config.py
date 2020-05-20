import logging
import os
import configparser


class ConfigReader:
    __config_filename = 'motion-monitor.ini'

    def __init__(self):
        self.__logger = logging.getLogger(__name__)
        self.__logger.info("Initialised...")

    def read_config(self, filename=None, ignore_defaults=False):
        config = configparser.RawConfigParser()

        if not ignore_defaults:
            # Attempt to read the defaults, from the possible locations.
            default_locations = [os.curdir, "/etc/motion-monitor"]
            self.__logger.debug("Default config locations: %s" % default_locations)
            for location in default_locations:
                try:
                    file_path = os.path.join(location, self.__config_filename + ".default")
                    self.__logger.debug("Attempting to read default config from %s" % file_path)
                    with open(file_path) as source:
                        config.read_file(source)
                        self.__logger.info("Read default config from %s" % file_path)
                        break
                except IOError:
                    self.__logger.error("Error reading default config from %s" % location)

        if filename:
            try:
                self.__logger.debug("Attempting to read specified config from %s" % filename)
                file_path = filename
                if os.path.exists(file_path):
                    config.read(file_path)
                    self.__logger.info("Overwrote defaults with config from %s" % file_path)
            except IOError:
                self.__logger.error("Error overwriting config from %s" % filename)
        else:
            # Attempt to overwrite the defaults with user specifics
            override_locations = [os.curdir, os.path.expanduser("~/.motion-monitor"), "/etc/motion-monitor"]
            for location in override_locations:
                try:
                    file_path = os.path.join(location, self.__config_filename)
                    if os.path.exists(file_path):
                        config.read(file_path)
                        self.__logger.info("Overwrote defaults with config from %s" % file_path)
                        break
                except IOError:
                    self.__logger.error("Error overwriting config from %s" % location)

        self.__logger.debug(config)

        return config
