'''
Created on 31/07/2013

@author: djwhyte
'''
from gi.repository import GObject
import logging

class SimpleLogger(GObject.GObject):
    
    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger(__name__)
        self.__logger.info("Initialised")
        
    def log_event(self, object, msg):
        self.__logger.debug("Printing: %s" % msg)
        print "SimpleLogger: %s" % msg