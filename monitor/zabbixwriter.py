'''
Created on 08/08/2013

@author: djwhyte
'''
import logging
import subprocess

class ZabbixWriter():
    
    __ZABBIX_KEY = "state"
    __ZABBIX_HOST = "camera%s"

    
    def __init__(self):
        
        self.__logger = logging.getLogger(__name__)
        
        self.__zabbix_server = "192.168.0.100"
        self.__logger.info("Initialised")

        
    def handle_camera_activity(self, object, camera):
        self.__logger.debug("Handling camera activity")
        
        camera_id = camera.get_id()
        value = camera.get_state()
        
        self.__logger.debug("Calling zabbix_sender with value of '%s' for key '%s' on camera %s"  % (str(value), self.__ZABBIX_KEY, camera_id))
        try:
            subprocess.call(['zabbix_sender', '-z', self.__zabbix_server, '-s', self.__ZABBIX_HOST % camera, '-k', self.__ZABBIX_KEY, '-o', str(value)])
        except OSError, e:
            self.__logger.exception(e)
            
        return True
