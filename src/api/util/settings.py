#!/usr/bin/evn python
#-*-coding:utf8-*-


import os, sys, json

DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)

class settings(object):
	filename = ''
	config = {}
	
	def __init__(self):
		pass
		
	def get_settings(self):
		"""Parses the settings from redis-live.conf.
		"""
		# TODO: Consider YAML. Human writable, machine readable.
		with open(self.filename) as fp:
			try:
				return json.load(fp)
			except Exception, e:
				if DEBUG:
					print >>sys.stderr, 'get_settings exception:', e
				return {}

	def get_redis_servers(self):		
		if DEBUG:
			print sys.stderr, "get_redis_servers config:%s"%self.config
		return self.config.get("RedisServers", '')
	
	
	def get_redis_stats_server(self):
		if DEBUG:
			print sys.stderr, "get_redis_stats_server config:%s"%self.config
		return self.config.get("RedisStatsServer", '')
	
	
	def get_data_store_type(self):
		if DEBUG:
			print sys.stderr, "get_redis_stats_server config:%s"%self.config
		return self.config.get("DataStoreType", '')
	
	
	def get_sqlite_stats_store(self):
		if DEBUG:
			print sys.stderr, "get_redis_stats_server config:%s"%self.config
		return self.config.get("SqliteStatsStore", '')
