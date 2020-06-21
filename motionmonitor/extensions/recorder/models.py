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

    event_id = pw.CharField()
    camera_id = pw.CharField()
    start_time = pw.DateTimeField()

    class Meta:
        table_name = "motion_event"

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

    camera_id = pw.CharField()
    timestamp = pw.DateTimeField()
    frame = pw.IntegerField()
    filename = pw.CharField()
    archive = pw.BooleanField()

    class Meta:
        table_name = "snapshot_frame"


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

    event_id = pw.CharField()
    camera_id = pw.CharField()
    timestamp = pw.DateTimeField()
    frame = pw.IntegerField()
    filename = pw.CharField()

    class Meta:
        table_name = "motion_frame"
