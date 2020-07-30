import unittest
from datetime import datetime

import peewee as pw

import motionmonitor
from motionmonitor.extensions.recorder import models
from motionmonitor.extensions.recorder.models import Event, Frame, EventFrame

CAMERA_ID = "1"
EVENT_ID = "202006011200-1"


class EventTableTests(unittest.TestCase):

    def setUp(self) -> None:
        sqlite_mem = pw.SqliteDatabase(":memory:")
        models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([Event], safe=False)

    def test_from_native(self):
        now = datetime.now()
        e = motionmonitor.models.Event(EVENT_ID, CAMERA_ID, now)
        db_event = Event.from_native(e)
        self.assertEqual(EVENT_ID, db_event.event_id)
        self.assertEqual(CAMERA_ID, db_event.camera_id)
        self.assertEqual(now, db_event.start_time)

        # Check the Event isn't added to the DB.
        events = Event.select()
        self.assertEqual(0, len(events))

    def test_to_native(self):
        now = datetime.now()
        e = Event(event_id=EVENT_ID, camera_id=CAMERA_ID, start_time=now)
        native_event = e.to_native()
        self.assertEqual(EVENT_ID, native_event.id)
        self.assertEqual(CAMERA_ID, native_event.camera_id)
        self.assertEqual(now, native_event.start_time)

        # Check the frame isn't added to the DB
        events = Event.select()
        self.assertEqual(0, len(events))


class FrameTableTests(unittest.TestCase):

    def setUp(self) -> None:
        sqlite_mem = pw.SqliteDatabase(":memory:")
        models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([Frame], safe=False)

    def test_from_native(self):
        now = datetime.now()
        filename = "filename.jpg"
        e = motionmonitor.models.Frame(CAMERA_ID, now, 0, filename)
        db_frame = Frame.from_native(e)
        self.assertEqual(CAMERA_ID, db_frame.camera_id)
        self.assertEqual(now, db_frame.timestamp)
        self.assertEqual(0, db_frame.frame)
        self.assertEqual(filename, db_frame.filename)

        # Check the Frame isn't added to the DB
        frames = Frame.select()
        self.assertEqual(0, len(frames))

    def test_to_native(self):
        now = datetime.now()
        filename = "filename.jpg"
        f = Frame(camera_id=CAMERA_ID, timestamp=now, frame=0, filename=filename)
        native_frame = f.to_native()
        self.assertEqual(CAMERA_ID, native_frame.camera_id)
        self.assertEqual(now, native_frame.timestamp)
        self.assertEqual(0, native_frame.frame_num)
        self.assertEqual(filename, native_frame.filename)

        # Check the frame isn't added to the DB
        frames = Frame.select()
        self.assertEqual(0, len(frames))


class EventFrameTableTests(unittest.TestCase):

    def setUp(self) -> None:
        sqlite_mem = pw.SqliteDatabase(":memory:")
        models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([EventFrame], safe=False)

    def test_from_native(self):
        now = datetime.now()
        filename = "filename.jpg"
        f = motionmonitor.models.EventFrame(CAMERA_ID, EVENT_ID, now, 0, filename, 100)
        db_frame = EventFrame.from_native(f)
        self.assertEqual(CAMERA_ID, db_frame.camera_id)
        self.assertEqual(EVENT_ID, db_frame.event_id)
        self.assertEqual(now, db_frame.timestamp)
        self.assertEqual(0, db_frame.frame)
        self.assertEqual(filename, db_frame.filename)
        self.assertEqual(100, db_frame.score)

        # Check the Frame isn't added to the DB
        frames = EventFrame.select()
        self.assertEqual(0, len(frames))

    def test_to_native(self):
        now = datetime.now()
        filename = "filename.jpg"
        f = EventFrame(camera_id=CAMERA_ID, event_id=EVENT_ID, timestamp=now, frame=0, filename=filename, score=100)
        native_frame = f.to_native()
        self.assertEqual(CAMERA_ID, native_frame.camera_id)
        self.assertEqual(EVENT_ID, native_frame.event_id)
        self.assertEqual(now, native_frame.timestamp)
        self.assertEqual(0, native_frame.frame_num)
        self.assertEqual(filename, native_frame.filename)
        self.assertEqual(100, native_frame.score)

        # Check the frame isn't added to the DB
        frames = EventFrame.select()
        self.assertEqual(0, len(frames))


if __name__ == '__main__':
    unittest.main()
