'''
Created on 08/08/2013

@author: djwhyte
'''
import logging
import subprocess

from motionmonitor.const import EVENT_CAMERA_ACTIVITY


class ZabbixWriter():
    
    __ZABBIX_KEY = "state"
    __ZABBIX_HOST = "camera%s"

    
    def __init__(self, mm):
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        config = mm.config

        # We care about camera activity, register a handler.
        self.mm.bus.listen(EVENT_CAMERA_ACTIVITY, self.handle_camera_activity)

        self.__zabbix_server = config.ZABBIX_SERVER_ADDR
        self.__logger.info("Initialised")

        
    def handle_camera_activity(self, event):
        try:
            self.__logger.debug("Handling camera activity")
            camera = event.data
        
            camera_id = camera.id
            value = camera.state
        
            self.__logger.debug("Calling zabbix_sender with value of '%s' for key '%s' on camera %s"  % (str(value), self.__ZABBIX_KEY, camera_id))
            try:
                process_args = ['zabbix_sender', '-z', self.__zabbix_server, '-s', self.__ZABBIX_HOST % camera_id, '-k', self.__ZABBIX_KEY, '-o', str(value)]
                self.__logger.debug("Calling subprocess: %s" % process_args)
                subprocess.call(process_args)
            except OSError as e:
                self.__logger.exception(e)
        
        except Exception as e:
            self.__logger.exception(e)
            raise
        return True