'''
Created on 08/08/2013

@author: djwhyte
'''
from gi.repository import GObject
import logging
import subprocess

class ZabbixWriter(GObject.GObject):
    
    __ZABBIX_KEY = "state"
    __ZABBIX_HOST = "camera%s"

    
    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger(__name__)
        
        self.__zabbix_server = "192.168.0.100"
        self.__logger.info("Initialised")

        
    def handle_msg(self, object, msg):
        if msg["type"] in ["event_end", "event_start"]:
            value = 0  # Idle
            if msg["type"] == "event_start":
                value = 2  # Alarm
                
            camera = msg["camera"]
            self.__logger.debug("Calling zabbix_sender with value of %s for key %s on camera %s"  % (str(value), self.__ZABBIX_KEY, camera))
            subprocess.call(['zabbix_sender', '-z', self.__zabbix_server, '-s', self.__ZABBIX_HOST % camera, '-k', self.__ZABBIX_KEY, '-o', str(value)])
