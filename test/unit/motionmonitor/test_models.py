import unittest

from motionmonitor.models import Camera, Frame, Event, EventFrame

CAMERA_ID = 1
EVENT_ID = "20200101-1"


class TestFrame(unittest.TestCase):
    pass


class TestEventFrame(unittest.TestCase):
    pass


class TestEvent(unittest.TestCase):

    def test_simple(self):
        # def __init__(self, event_id, camera_id, start_time):
        e = Event(EVENT_ID, CAMERA_ID, "timestamp")
        self.assertEqual(EVENT_ID, e.id)
        self.assertEqual(CAMERA_ID, e.camera_id)
        self.assertIsNone(e.top_score_frame)

    def test_get_json(self):
        import json
        e = Event(EVENT_ID, CAMERA_ID, "timestamp")
        json_str = e.to_json()
        # Check it can be parsed as JSON
        json_obj = json.dumps(json_str)
        self.assertIsNotNone(json_obj)

    def test_append_frame(self):
        e = Event(EVENT_ID, CAMERA_ID, "timestamp")
        self.assertIsNone(e.top_score_frame)

        # Add a frame to the event
        ef1 = EventFrame(CAMERA_ID, EVENT_ID, "timestamp1", 0, "filename1", 100)
        e.append_frame(ef1)
        self.assertEqual(ef1, e.top_score_frame)

        # Add a higher scoring frame to the event
        ef2 = EventFrame(CAMERA_ID, EVENT_ID, "timestamp2", 1, "filename2", 200)
        e.append_frame(ef2)
        self.assertEqual(ef2, e.top_score_frame)
        self.assertNotEqual(ef1, ef2)

        # If we add a lower scoring frame, it shouldn't be the top scorer.
        e.append_frame(ef1)
        self.assertEqual(ef2, e.top_score_frame)


class TestCamera(unittest.TestCase):

    def test_simple(self):
        c = Camera(CAMERA_ID)
        self.assertEqual(CAMERA_ID, c.id)
        self.assertEqual(Camera.STATE_IDLE, c.state)
        self.assertIsNone(c.last_snapshot)
        self.assertEqual(0, len(c.recent_motion))

    def test_get_json(self):
        import json
        c = Camera(CAMERA_ID)
        json_str = c.to_json()
        # Check it can be parsed as JSON
        json_obj = json.dumps(json_str)
        self.assertIsNotNone(json_obj)

    def test_append_snapshot_frame(self):
        c = Camera(CAMERA_ID)
        self.assertIsNone(c.last_snapshot)

        # Add a snapshot frame
        f1 = Frame(Camera, "timestamp1", 0, "filename1")
        c.append_snapshot_frame(f1)
        self.assertEqual(f1, c.last_snapshot)

        # Add another snapshot frame
        f2 = Frame(Camera, "timestamp2", 1, "filename2")
        c.append_snapshot_frame(f2)
        self.assertEqual(f2, c.last_snapshot)
        self.assertNotEqual(f1, f2)



if __name__ == '__main__':
    unittest.main()
