#!/usr/bin/env python

from distutils.core import setup

version = '0.01'

data = dict(
    name = 'motion-monitor',
    version = version,
    description = 'motion-monitor is used to motionmonitor and handle events relating to the motion security camera software',
    author = 'David Whyte',
    author_email = 'david@thewhytehouse.org',
    packages =      ['motionmonitor', 'motionmonitor.stream', 'motionmonitor.extensions'],
    scripts = ['motion-monitor'],
    data_files = [('/etc/init', ['motion-monitor.conf']),
                  ('/etc/apache2/sites-enabled', ['motion-monitor_apache.conf']),
                  ('/var/www/motion-monitor', ['html/index.html', 'html/io.js', 'html/camerasummary.js', 'html/jpegimage.js']),
                  ('/var/www/motion-monitor/wsgi', ['json.wsgi', 'media.wsgi'])],
    )


setup(**data)