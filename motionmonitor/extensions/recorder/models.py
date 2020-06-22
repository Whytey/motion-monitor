import peewee as pw

import motionmonitor

proxy = pw.DatabaseProxy()


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
        return Event.create(event_id=event.id, camera_id=event.camera_id, start_time=event.start_time)

    def to_native(self) -> motionmonitor.models.Event:
        return motionmonitor.models.Event(self.event_id, self.camera_id, self.start_time)


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

    archive = pw.IntegerField(null=True)
    camera_id = pw.IntegerField()
    filename = pw.CharField(null=True, unique=True)
    frame = pw.IntegerField(null=True)
    timestamp = pw.DateTimeField()

    class Meta:
        table_name = 'snapshot_frame'
        indexes = (
            (('timestamp', 'camera_id'), False),
        )
        primary_key = False


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
