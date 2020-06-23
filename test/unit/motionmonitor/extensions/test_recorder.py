import asyncio
import unittest
from datetime import datetime
from unittest.mock import Mock

import motionmonitor
from motionmonitor.core import EventBus
from motionmonitor.extensions.recorder import Recorder
from motionmonitor.extensions.recorder import models as db_models
from motionmonitor.models import Event, Frame, EventFrame


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mm = Mock()
        self.mm.config = {"RECORDER": {"URL": "sqlite:///:memory:"}}
        self.mm.bus = EventBus(self.mm)
        self.mm.loop = asyncio.new_event_loop()
        recorder = Recorder(self.mm)

        self.mm.loop.run_until_complete(recorder.start_extension())

    def test_get_extension(self):
        from motionmonitor.extensions.recorder import get_extension
        extensions = get_extension(self.mm)
        self.assertEqual(1, len(extensions))
        self.assertIsInstance(extensions[0], Recorder)

    def test_handle_event(self):
        event = Event("EVENTID", "CAMERAID", datetime.now())
        self.mm.bus.fire(motionmonitor.const.EVENT_MOTION_EVENT_START, event)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.Event.select().count())

    def test_handle_snapshot_frame(self):
        frame = Frame("CAMERAID", datetime.now(), 0, "filename.jpg")
        self.mm.bus.fire(motionmonitor.const.EVENT_NEW_FRAME, frame)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.Frame.select().count())

    def test_handle_motion_frame(self):
        frame = EventFrame("CAMERAID", "EVENTID", datetime.now(), 0, "filename.jpg", 100)
        self.mm.bus.fire(motionmonitor.const.EVENT_NEW_MOTION_FRAME, frame)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.EventFrame.select().count())


if __name__ == '__main__':
    unittest.main()
