import logging

import peewee as pw

import motionmonitor

proxy = pw.DatabaseProxy()

SCHEMA_VERSION = 1
_LOGGER = logging.getLogger(__name__)


class BaseModel(pw.Model):
    class Meta:
        database = proxy


class Event(BaseModel):
    # motion_event:
    # +------------+-------------+------+-----+---------+-------+
    # | Field      | Type        | Null | Key | Default | Extra |
    # +------------+-------------+------+-----+---------+-------+
    # | event_id   | varchar(40) | NO   | PRI | NULL    |       |
    # | camera_id  | int(11)     | NO   | PRI | NULL    |       |
    # | start_time | datetime    | NO   | MUL | NULL    |       |
    # +------------+-------------+------+-----+---------+-------+

    camera_id = pw.IntegerField()
    event_id = pw.CharField()
    start_time = pw.DateTimeField()

    class Meta:
        table_name = 'motion_event'
        indexes = (
            (('event_id', 'camera_id'), True),
            (('start_time', 'camera_id'), False),
        )
        primary_key = False

    @staticmethod
    def from_native(event):
        return Event(event_id=event.id,
                     camera_id=event.camera_id,
                     start_time=event.start_time)

    def to_native(self) -> motionmonitor.models.Event:
        return motionmonitor.models.Event(self.event_id,
                                          self.camera_id,
                                          self.start_time)


class Frame(BaseModel):
    # snapshot_frame:
    # +-----------+--------------+------+-----+---------+-------+
    # | Field     | Type         | Null | Key | Default | Extra |
    # +-----------+--------------+------+-----+---------+-------+
    # | camera_id | int(11)      | NO   |     | NULL    |       |
    # | timestamp | datetime     | NO   | MUL | NULL    |       |
    # | frame     | int(11)      | YES  |     | NULL    |       |
    # | filename  | varchar(100) | YES  | UNI | NULL    |       |
    # | archive   | tinyint(1)   | YES  |     | NULL    |       |
    # +-----------+--------------+------+-----+---------+-------+

    camera_id = pw.IntegerField()
    timestamp = pw.DateTimeField()
    frame = pw.IntegerField(null=True)
    filename = pw.CharField(null=True, unique=True)
    archive = pw.IntegerField(null=True)

    class Meta:
        table_name = 'snapshot_frame'
        indexes = (
            (('timestamp', 'camera_id'), False),
        )
        primary_key = False

    @staticmethod
    def from_native(frame):
        return Frame(camera_id=frame.camera_id,
                     timestamp=frame.timestamp,
                     frame=frame.frame_num,
                     filename=frame.filename,
                     archive=0)

    def to_native(self) -> motionmonitor.models.Frame:
        return motionmonitor.models.Frame(self.camera_id,
                                          self.timestamp,
                                          self.frame,
                                          self.filename)


class EventFrame(BaseModel):
    # motion_frame:
    # +-----------+--------------+------+-----+---------+-------+
    # | Field     | Type         | Null | Key | Default | Extra |
    # +-----------+--------------+------+-----+---------+-------+
    # | event_id  | varchar(40)  | NO   | MUL | NULL    |       |
    # | camera_id | int(11)      | NO   |     | NULL    |       |
    # | timestamp | datetime     | NO   |     | NULL    |       |
    # | frame     | int(11)      | YES  |     | NULL    |       |
    # | score     | int(11)      | YES  |     | NULL    |       |
    # | filename  | varchar(100) | YES  |     | NULL    |       |
    # +-----------+--------------+------+-----+---------+-------+

    camera_id = pw.IntegerField()
    event_id = pw.CharField(index=True)
    filename = pw.CharField(null=True)
    frame = pw.IntegerField(null=True)
    score = pw.IntegerField(null=True)
    timestamp = pw.DateTimeField()

    class Meta:
        table_name = 'motion_frame'
        indexes = (
            (('event_id', 'camera_id', 'timestamp', 'frame'), True),
        )
        primary_key = False

    @staticmethod
    def from_native(frame):
        return EventFrame(camera_id=frame.camera_id,
                          event_id=frame.event_id,
                          timestamp=frame.timestamp,
                          frame=frame.frame_num,
                          filename=frame.filename,
                          score=frame.score)

    def to_native(self) -> motionmonitor.models.Frame:
        return motionmonitor.models.EventFrame(self.camera_id,
                                               self.event_id,
                                               self.timestamp,
                                               self.frame,
                                               self.filename,
                                               self.score)
