import unittest
from datetime import datetime

import peewee as pw

import motionmonitor
import motionmonitor.extensions.recorder.models as db
from motionmonitor.extensions.recorder.models import Event

CAMERA_ID = "1"
EVENT_ID = "202006011200-1"


class EventTableTests(unittest.TestCase):

    def setUp(self) -> None:
        sqlite_mem = pw.SqliteDatabase(":memory:")
        self.db = db
        self.db.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db.Event], safe=False)

    def test_from_native(self):
        now = datetime.now()
        e = motionmonitor.models.Event(EVENT_ID, CAMERA_ID, now)
        db_event = Event.from_native(e)
        self.assertEqual(EVENT_ID, db_event.event_id)
        self.assertEqual(CAMERA_ID, db_event.camera_id)
        self.assertEqual(now, db_event.start_time)

    def test_to_native(self):
        now = datetime.now()
        e = Event.create(event_id=EVENT_ID, camera_id=CAMERA_ID, start_time=now)
        native_event = e.to_native()
        self.assertEqual(EVENT_ID, native_event.id)
        self.assertEqual(CAMERA_ID, native_event.camera_id)
        self.assertEqual(now, native_event.start_time)

        events = self.db.Event.select()
        self.assertEqual(1, len(events))


if __name__ == '__main__':
    unittest.main()
