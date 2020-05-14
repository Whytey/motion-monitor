#!/usr/bin/env python

from distutils.core import setup

version = '0.02'

data = dict(
    name = 'motion-monitor',
    version = version,
    description = 'motion-monitor is used to monitor and handle events relating to the motion security camera software',
    author = 'David Whyte',
    author_email = 'david@thewhytehouse.org',
    packages =      ['motionmonitor', 'motionmonitor.stream', 'motionmonitor.extensions'],
    scripts = ['motion-monitor'],
    data_files = [('/etc/init', ['motion-monitor.conf']),],
    )


setup(**data)