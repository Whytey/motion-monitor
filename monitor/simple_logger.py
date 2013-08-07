'''
Created on 31/07/2013

@author: djwhyte
'''
from gi.repository import GObject

class SimpleLogger(GObject.GObject):
    
    def __init__(self):
        GObject.GObject.__init__(self)
        
    def log_event(self, object, msg):
        print "SimpleLogger: %s" % msg