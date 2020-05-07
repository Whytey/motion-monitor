#!/usr/bin/env python

from distutils.core import setup

version = '0.01'

data = dict(
    name = 'motion-motionmonitor',
    version = version,
    description = 'motion-motionmonitor is used to motionmonitor and handle events relating to the motion security camera software',
    author = 'David Whyte',
    author_email = 'david@thewhytehouse.org',
    packages =      ['motionmonitor', 'motionmonitor.stream', 'motionmonitor.extensions'],
    scripts = ['motion-motionmonitor'],
    data_files = [('/etc/init', ['motion-motionmonitor.conf']),
                  ('/etc/apache2/sites-enabled', ['motion-monitor_apache.conf']),
                  ('/var/www/motion-motionmonitor', ['html/index.html', 'html/io.js', 'html/camerasummary.js', 'html/jpegimage.js']),
                  ('/var/www/motion-motionmonitor/wsgi', ['json.wsgi', 'media.wsgi'])],
    )


setup(**data)