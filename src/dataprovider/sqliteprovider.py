import os, sys
from api.util import settings
import contextlib
import sqlite3
import json



class RedisStatsProvider(object):
	"""A Sqlite based persistance to store and fetch stats
	"""

	def __init__(self):
		self.DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)
		stats = settings.settings().get_sqlite_stats_store()
		self.location = stats.get('path', 'db/redislive.dat')
		self.retries = 10
		self.conn = sqlite3.connect(self.location)
		

	def save_memory_info(self, server, timestamp, used, peak):
		"""Saves used and peak memory stats,

		Args:
			server (str): The server ID
			timestamp (datetime): The time of the info.
			used (int): Used memory value.
			peak (int): Peak memory value.
		"""
		query = "INSERT INTO memory VALUES (?, ?, ?, ?);"
		values = (timestamp, used, peak, server)
		try:
			self._retry_query(query, values)
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save memory info [server = %s] to sqlite %s err:%s'%(server, self.location, e)
			return False

	def save_command_info(self, server, timestamp, total_command):
		"""Saves process stats,

		Args:
			server (str): The server ID
			timestamp (datetime): The time of the info.
			total_command (int): total command value.
		"""
		query = "INSERT INTO command VALUES (?, ?, ?);"
		values = (timestamp, total_command, server)
		try:
			self._retry_query(query, values)
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save command info [server = %s] to sqlite %s err:%s'%(server, self.location, e)
			return False
				
	def save_info_command(self, server, timestamp, info):
		"""Save Redis info command dump

		Args:
			server (str): id of server
			timestamp (datetime): Timestamp.
			info (dict): The result of a Redis INFO command.
		"""
		query = "INSERT INTO info VALUES (?, ?, ?);"
		values = (timestamp, json.dumps(info),
				  server)
		try:
			self._retry_query(query, values)
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save info command [server = %s] to sqlite %s err:%s'%(server, self.location, e)
			return False

	def get_info(self, server):
		"""Get info about the server

		Args:
			server (str): The server ID
		"""
		with contextlib.closing(self.conn.cursor()) as c:
			query = "SELECT info FROM info WHERE server=?"
			query += "ORDER BY datetime DESC LIMIT 1;"
			for r in c.execute(query, (server,)):
				return(json.loads(r[0]))

	def get_memory_info(self, server, from_date, to_date):
		"""Get stats for Memory Consumption between a range of dates

		Args:
			server (str): The server ID
			from_date (datetime): Get memory info from this date onwards.
			to_date (datetime): Get memory info up to this date.
		"""

		query = """SELECT datetime, max, current
		FROM memory
		WHERE datetime >= ?
		AND datetime <= ?
		AND server = ?;"""

		values = (from_date, to_date, server)

		with contextlib.closing(self.conn.cursor()) as c:
			return [[r[0], r[1], r[2]] for r in c.execute(query, values)]

	def get_command_stats(self, server, from_date, to_date):
		"""Get total commands processed in the given time period

		Args:
			server (str): The server ID
			from_date (datetime): Get data from this date.
			to_date (datetime): Get data to this date.
			group_by (str): How to group the stats.
		"""

		query = """SELECT datetime, max, current
		FROM command
		WHERE datetime >= ?
		AND datetime <= ?
		AND server = ?;"""

		values = (from_date, to_date, server)

		with contextlib.closing(self.conn.cursor()) as c:
			return [[r[0], r[1], r[2]] for r in c.execute(query, values)]

	def _retry_query(self, query, values=None):
		"""Run a SQLite query until it sticks or until we reach the max number
		of retries. Single-threaded writes :(

		Args:
			query (str): The query to execute.

		Kwargs:
			values (tuple|dict): Used when the query is parameterized.
		"""
		with contextlib.closing(self.conn.cursor()) as cursor:
			completed = False
			counter = 0
			while counter < self.retries and not completed:
				counter += 1
				try:
					cursor.execute(query, values)
					self.conn.commit()
					completed = True
				except Exception:
					# FIXME: Catch specific exceptions here otherwise it's likely to
					# mask bugs/issues later.
					pass
