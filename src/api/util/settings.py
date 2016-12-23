#!/usr/bin/evn python
#-*-coding:utf8-*-


import json

class settings(object):
	def __init__(self, filename):
		self.file = filename
		self.get_settings()
		
	def get_settings(self):
	    """Parses the settings from redis-live.conf.
	    """
	    # TODO: Consider YAML. Human writable, machine readable.
	    with open(self.filename) as config:
	        self.config = json.load(config)
	

	def get_redis_servers(self):
	    return self.config["RedisServers"]
	
	
	def get_redis_stats_server(self):
	    return self.config["RedisStatsServer"]
	
	
	def get_data_store_type(self):
	    return self.config["DataStoreType"]
	
	
	def get_sqlite_stats_store(self):
	    return self.config["SqliteStatsStore"]
