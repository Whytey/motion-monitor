'''
Created on 08/08/2013

@author: djwhyte
'''
import logging
import subprocess
# import asyncio

from motionmonitor.const import EVENT_CAMERA_ACTIVITY


def get_extension(mm):
    return ZabbixWriter(mm)


class ZabbixWriter():
    __ZABBIX_KEY = "state"
    __ZABBIX_HOST = "camera%s"

    def __init__(self, mm):
        self.__logger = logging.getLogger(__name__)
        self.mm = mm
        self.__zabbix_server = self.mm.config["ZABBIX"]["SERVER_ADDRESS"]
        self.__logger.info("Initialised")


    async def start_extension(self):
        # We care about camera activity, register a handler.
        self.mm.bus.listen(EVENT_CAMERA_ACTIVITY, self.handle_camera_activity)
        self.__logger.info("Started")

    def handle_camera_activity(self, event):
        try:
            print("Activity")
            self.__logger.debug("Handling camera activity")
            camera = event.data

            camera_id = camera.id
            value = camera.state

            self.__logger.debug("Calling zabbix_sender with value of '%s' for key '%s' on camera %s" % (
                str(value), self.__ZABBIX_KEY, camera_id))
            try:
                process_args = ['zabbix_sender', '-z', self.__zabbix_server, '-s', self.__ZABBIX_HOST % camera_id, '-k',
                                self.__ZABBIX_KEY, '-o', str(value)]
                self.__logger.debug("Calling subprocess: %s" % process_args)
                subprocess.call(process_args)
            except OSError as e:
                self.__logger.exception(e)

        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
