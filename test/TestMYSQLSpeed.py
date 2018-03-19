import unittest
import datetime
from time import time
import MySQLdb
from MySQLdb.cursors import SSCursor

timeNow = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

class TestMysql(unittest.TestCase):

    def __get_vquick_query(self):
	return """SELECT count(*) FROM snapshot_frame a
		WHERE (timestamp < subdate(%s, INTERVAL 7 DAY)
		     AND minute(timestamp) != 0)
		OR (timestamp < subdate(%s, INTERVAL 4 WEEK)
		     AND hour(timestamp) NOT IN (6,12, 18)
		     AND minute(timestamp) != 0)
		OR (timestamp < subdate(%s, INTERVAL 3 MONTH)
		     AND hour(timestamp) != 12
		     AND minute(timestamp) != 0)""" %(timeNow, timeNow, timeNow)

    def __get_non_union_query(self):
        return """CREATE
	TEMPORARY TABLE IF NOT EXISTS retain_frames (INDEX idx_time_camera (timestamp, camera_id)) AS
	SELECT camera_id,
	  timestamp,
	  frame,
	  filename
	FROM (SELECT camera_id,
	   timestamp,
	   frame,
	   filename
	FROM snapshot_frame a
	WHERE timestamp >= subdate(%s, INTERVAL 7 DAY)
	OR (timestamp < subdate(%s, INTERVAL 7 DAY)
	AND timestamp >= subdate(%s, INTERVAL 4 WEEK)
	AND minute(timestamp) = 0)
	OR (timestamp < subdate(%s, INTERVAL 4 WEEK)
	AND timestamp >= subdate(%s, INTERVAL 3 MONTH)
	AND hour(timestamp) IN (6,
		              12,
		              18)
	AND minute(timestamp) = 0)
	OR (timestamp < subdate(%s, INTERVAL 3 MONTH)
	AND hour(timestamp) = 12
	AND minute(timestamp) = 0)) e""" % (timeNow,
                                            timeNow,
                                            timeNow,
                                            timeNow,
                                            timeNow,
                                            timeNow)


    def __get_create_query(self):
        return """CREATE
                   TEMPORARY TABLE IF NOT EXISTS retain_frames (INDEX idx_time_camera (timestamp, camera_id)) AS
                   SELECT camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM (
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame a
                            WHERE timestamp >= subdate(%s, INTERVAL 7 DAY))
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame b
                            WHERE timestamp < subdate(%s, INTERVAL 7 DAY)
                              AND timestamp >= subdate(%s, INTERVAL 4 WEEK)
                              AND minute(timestamp) = 0)
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame c
                            WHERE timestamp < subdate(%s, INTERVAL 4 WEEK)
                              AND timestamp >= subdate(%s, INTERVAL 3 MONTH)
                              AND hour(timestamp) IN (6,
                                                      12,
                                                      18)
                              AND minute(timestamp) = 0)
                         UNION
                           (SELECT camera_id,
                                   timestamp,
                                   frame,
                                   filename
                            FROM snapshot_frame d
                            WHERE timestamp < subdate(%s, INTERVAL 3 MONTH)
                              AND hour(timestamp) = 12
                              AND minute(timestamp) = 0)) e""" % (timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow,
                                                                 timeNow)

    def __get_select_query(self):
        return """SELECT camera_id,
                          timestamp,
                          frame,
                          filename
                   FROM snapshot_frame a
                   WHERE timestamp < %s
                     AND NOT EXISTS
                       (SELECT camera_id,
                               timestamp,
                               frame,
                               filename
                        FROM retain_frames b
                        WHERE a.camera_id = b.camera_id
                          AND a.timestamp = b.timestamp
                          AND a.frame = b.frame)""" % timeNow

    def __run_query(self, cursor, queries):
        tic = time()
        for query in queries:
            cursor.execute(query)
            print query
            print "So far: " + str(time() - tic)

        counter = 0
        for row in cursor:
           counter = counter + 1
        print "Count: " + str(counter)
        toc = time()
        return str(toc - tic)


    def testBaseline(self):

        cnx = MySQLdb.connect("127.0.0.1", "motion", "motion", "motion")
	cursors = {"SSCursor": SSCursor(cnx), "Normal": cnx.cursor}
        queries = [self.__get_create_query(), self.__get_select_query()]
	for k, cursor in cursors.iteritems():
		print "{}: took {} seconds".format(k, self.__run_query(cursor, queries))

    def testNonUnion(self):

        cnx = MySQLdb.connect("127.0.0.1", "motion", "motion", "motion")
	cursors = {"SSCursor": SSCursor(cnx), "Normal": cnx.cursor}
        queries = [self.__get_non_union_query(), self.__get_select_query()]
	for k, cursor in cursors.iteritems():
		print "{}: took {} seconds".format(k, self.__run_query(cursor, queries))
		
    def testSimpleSelect(self):

        cnx = MySQLdb.connect("127.0.0.1", "motion", "motion", "motion")
	cursors = {"SSCursor": SSCursor(cnx), "Normal": cnx.cursor}
        queries = [self.__get_vquick_query()]
	for k, cursor in cursors.iteritems():
		print "{}: took {} seconds".format(k, self.__run_query(cursor, queries))
		
if __name__ == '__main__':
    unittest.main()
