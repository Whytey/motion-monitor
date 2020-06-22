import asyncio
import unittest
from datetime import datetime
from unittest.mock import Mock

import motionmonitor
from motionmonitor.core import EventBus
from motionmonitor.extensions.recorder import Recorder
from motionmonitor.models import Event
import peewee as pw
from motionmonitor.extensions.recorder import models


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mm = Mock()
        self.mm.config = {"RECORDER": {"URL": "sqlite:///:memory:"}}
        self.mm.bus = EventBus(self.mm)
        self.mm.loop = asyncio.new_event_loop()
        recorder = Recorder(self.mm)

        self.mm.loop.run_until_complete(recorder.start_extension())

    def test_handle_event(self):
        event = Event("EVENTID", "CAMERAID", datetime.now())
        self.mm.bus.fire(motionmonitor.const.EVENT_MOTION_EVENT_START, event)

        self.assertEqual(1, models.Event.select().count())


if __name__ == '__main__':
    unittest.main()
