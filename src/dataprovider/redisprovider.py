import os, sys
from api.util import settings
from datetime import datetime, timedelta
import redis
import json
import ast



class RedisStatsProvider(object):
	"""A Redis based persistance to store and fetch stats"""

	def __init__(self):
		self.DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)
		# redis server to use to store stats
		stats_server = settings.settings().get_redis_stats_server()
		self.server = stats_server["server"]
		self.port = stats_server["port"]
		self.password = stats_server.get("password")
		self.conn = redis.StrictRedis(host=self.server, port=self.port, db=0, password=self.password)

	def save_memory_info(self, server, timestamp, used, peak):
		"""Saves used and peak memory stats,

		Args:
			server (str): The server ID
			timestamp (datetime): The time of the info.
			used (int): Used memory value.
			peak (int): Peak memory value.
		"""
		data = {"timestamp": timestamp,
				"used": used,
				"peak": peak}
		try:
			self.conn.zadd(server + ":memory", timestamp, data)
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save memory info [key = %s] to %s:%i err:%e'%(server, self.server, self.port, e)
			
			return False

	def save_command_info(self, server, timestamp, total_command):
		"""Saves process stats,

		Args:
			server (str): The server ID
			timestamp (datetime): The time of the info.
			total_command (int): total command value.
		"""
		data = {"timestamp": timestamp,
				"command": total_command}
		try:
			self.conn.zadd(server + ":command", timestamp, data)
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save command info [key = %s] to redis %s:%i err:%e'%(server, self.server, self.port, e)
			
			return False
				
	def save_info_command(self, server, timestamp, info):
		"""Save Redis info command dump

		Args:
			server (str): id of server
			timestamp (datetime): Timestamp.
			info (dict): The result of a Redis INFO command.
		"""
		try:
			self.conn.set(server + ":Info", json.dumps(info))
			return True
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Save info command [key = %s] to redis %s:%i err:%e'%(server, self.server, self.port, e)
			
			return False

	def get_info(self, server):
		"""Get info about the server

		Args:
			server (str): The server ID
		"""
		try:
			info = self.conn.get(server + ":Info")
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Get info [key = %s] from redis %s:%i err:%e'%(server, self.server, self.port, e)
			return ''
		# FIXME: If the collector has never been run we get a 500 here. `None`
		# is not a valid type to pass to json.loads.
		info = json.loads(info)
		return info

	def get_memory_info(self, server, start, end):
		"""Get stats for Memory Consumption between a range of dates

		Args:
			server (str): The server ID
			from_date (datetime): Get memory info from this date onwards.
			to_date (datetime): Get memory info up to this date.
		"""
		memory_data = []
		try:
			rows = self.conn.zrangebyscore(server + ":memory", start, end)
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Get memory info [key = %s] from redis %s:%i err:%e'%(server, self.server, self.port, e)
			return ''
					
		for row in rows:
			# TODO: Check to see if there's not a better way to do this. Using
			# eval feels like it could be wrong/dangerous... but that's just a
			# feeling.
			row = ast.literal_eval(row)

			# convert the timestamp
			timestamp = row['timestamp']

			memory_data.append([timestamp, row['peak'], row['used']])

		return memory_data

	def get_command_stats(self, server, start, end):
		"""Get total commands processed in the given time period

		Args:
			server (str): The server ID
			from_date (datetime): Get data from this date.
			to_date (datetime): Get data to this date.
		"""
		command_data = []
		try:
			rows = self.conn.zrangebyscore(server + ":command", start, end)
		except Exception, e:
			if self.DEBUG:
				print >>sys.stderr, 'Get command info [key = %s] from redis %s:%i err:%e'%(server, self.server, self.port, e)
			return ''
		
		for row in rows:
			# TODO: Check to see if there's not a better way to do this. Using
			# eval feels like it could be wrong/dangerous... but that's just a
			# feeling.
			row = ast.literal_eval(row)

			# convert the timestamp
			timestamp = row['timestamp']

			command_data.append([timestamp, row['command']])

		return command_data