import peewee


class Event(peewee.Model):
    # motion_event:
    # +------------+-------------+------+-----+---------+-------+
    # | Field      | Type        | Null | Key | Default | Extra |
    # +------------+-------------+------+-----+---------+-------+
    # | event_id   | varchar(40) | NO   | PRI | NULL    |       |
    # | camera_id  | int(11)     | NO   | PRI | NULL    |       |
    # | start_time | datetime    | NO   | MUL | NULL    |       |
    # +------------+-------------+------+-----+---------+-------+

    event_id = peewee.CharField()
    camera_id = peewee.CharField()
    start_time = peewee.DateTimeField()

    class Meta:
        database = None
        db_table = "motion_event"


class Frame(peewee.Model):
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

    camera_id = peewee.CharField()
    timestamp = peewee.DateTimeField()
    frame = peewee.IntegerField()
    filename = peewee.CharField()
    archive = peewee.BooleanField()

    class Meta:
        db_table = "snapshot_frame"


class EventFrame(peewee.Model):
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

    event_id = peewee.CharField()
    camera_id = peewee.CharField()
    timestamp = peewee.DateTimeField()
    frame = peewee.IntegerField()
    filename = peewee.CharField()

    class Meta:
        db_table = "motion_frame"
