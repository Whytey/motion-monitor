#!/usr/bin/env python

from distutils.core import setup
import os

version = '0.01'

data = dict(
    name = 'motion-monitor',
    version = version,
    description = 'motion-monitor is used to monitor and handle events relating to the motion security camera software',
    author = 'David Whyte',
    author_email = 'david@thewhytehouse.org',
    packages =      ['monitor'],
    scripts = ['motion-monitor'],
    data_files = [('/etc/init', ['motion-monitor.conf']), 
                  ('/etc/apache2/sites-enabled', ['motion-monitor_apache.conf']),
                  ('/var/www/motion-monitor/wsgi', ['motion-monitor.wsgi'])],
    )


setup(**data)