#! /usr/bin/env python
#-*-coding:utf8 -*-

import os, sys, time, datetime
from api.util.settings import settings
from dataprovider.dataprovider import RedisLiveDataProvider
from threading import Timer
import redis 
import threading
import traceback
import argparse

DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)


class InfoThread(threading.Thread):
	"""Runs a thread to execute the INFO command against a given Redis server
	and store the resulting statistics in the configured stats provider.
	"""

	def __init__(self, server, port, password=None, interval = 10):
		"""Initializes an InfoThread instance.

		Args:
			server (str): The host name of IP of the Redis server to monitor.
			port (int): The port number of the Redis server to monitor.

		Kwargs:
			password (str): The password to access the Redis server. \
					Default: None
		"""
		threading.Thread.__init__(self)
		self.server = server
		self.port = port
		self.password = password
		self.interval = interval
		self.id = self.server + ":" + str(self.port)
		self._stop = threading.Event()

	def stop(self):
		"""Stops the thread.
		"""
		self._stop.set()

	def stopped(self):
		"""Returns True if the thread is stopped, False otherwise.
		"""
		return self._stop.is_set()

	def run(self):
		"""Does all the work.
		"""
		stats_provider = RedisLiveDataProvider().get_provider()
		if not stats_provider:
			print >>sys.stderr, 'Get data provider error'
			sys.exit(4)
	
		redis_client = redis.StrictRedis(host=self.server, port=self.port, db=0,
										password=self.password)
	
		# process the results from redis
		num = 10
		while not self.stopped():
			if num >= self.interval:
				num = 1
				
				try:
					redis_info = redis_client.info()
				except Exception, e:
					print >>sys.stderr, 'Connect to Redis %s:%i err: %s'%(self.server, self.port, e)
					sys.exit(3)

				if DEBUG:
					print 'Get Redis %s:%i info:%s'%(self.server, self.port, redis_info)
					
				current_time = datetime.datetime.now()
				used_memory = int(redis_info['used_memory'])

				# used_memory_peak not available in older versions of redis
				try:
					peak_memory = int(redis_info['used_memory_peak'])
				except:
					peak_memory = used_memory

				if not stats_provider.save_memory_info(self.id, current_time, 
												used_memory, peak_memory):
					print >>sys.stderr, 'Save memory error'
					
				if not stats_provider.save_info_command(self.id, current_time, 
												 redis_info):
					print >>sys.stderr, 'Save info error'

			else:
				num += 1
			
			time.sleep(1)
		
		if self.stopped():
			print 'Recv stop signal, exit...'
			
class RedisMonitor(object):
	def __init__(self):
		self.threads = []
		self.active = True

	def run(self, config, duration, interval):
		"""Monitors all redis servers defined in the config for a certain number
		of seconds.

		Args:
			duration (int): The number of seconds to monitor for.
		"""

		#init settings
		settings.filename = config
		settings.config = settings().get_settings()
		
		redis_servers = settings().get_redis_servers()
		if not redis_servers:
			print >>sys.stderr, "Configure error"
			sys.exit(2)
	
		for redis_server in redis_servers:
			redis_password = redis_server.get("password", '')
			if "" in (redis_server.get("server", ""), redis_server.get("port", ""), redis_server.get("name", "")):
				print >>sys.stderr, "Configure invalid. RedisServers must configure the [server], [port], [name]"
				sys.exit(2)
			
			'''
			monitor = MonitorThread(redis_server["server"], redis_server["port"], redis_password)
			self.threads.append(monitor)
			monitor.setDaemon(True)
			monitor.start()
			'''
			
			info = InfoThread(redis_server["server"], redis_server["port"], redis_password, interval)
			self.threads.append(info)
			info.setDaemon(True)
			info.start()

		if duration:
			Timer(duration, self.stop).start()

		try:
			while self.active:
				time.sleep(1)
		except KeyboardInterrupt:
			print >>sys.stderr, "Recv Ctrl+C, process will exit..."
			self.stop()
			if duration:
				t.cancel()
		
		while threading.active_count() > 1:
			time.sleep(1)
			
	def stop(self):
		"""Stops the monitor and all associated threads.
		"""
		
		for t in self.threads:
				t.stop()
		self.active = False


def daemon(log):
	os.umask(0)
	
	pid = os.fork()        
	if pid > 0:
		sys.exit(0)
	
	os.setsid()
	pid = os.fork()
	if pid > 0:
		sys.exit(0)
	
	for i in range(1024):
		try:
			os.close(i)
		except:
			continue
	
	sys.stdin = open("/dev/null", "w+")
	sys.stdout = open(log, 'a')
	sys.stderr = sys.stdout

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Monitor redis.')
	parser.add_argument('--duration',
						type = int,
						help = "duration to run the monitor command (in seconds), default 0",
						required = False,
						default = 0)

	parser.add_argument('--interval',
						type = int,
						help = "interval to run the monitor command (in seconds) default 10",
						required = False,
						default = 10)

	parser.add_argument('--daemon',
						action = 'store_true',
						help = "run as a deamon server",
						required = False)

	parser.add_argument('--log',
						help = "special log file path(only used for daemon mode)",
						required = False)

	parser.add_argument('-f',
						metavar = 'CONFIG',
						help = "special config file(default ./redis-live.conf)",
						required = False,
						default = 'redis-live.conf')

	parser.add_argument('-d',
						action = 'store_true',
						help = "Open Debug mode",
						required = False)	
		
	args = parser.parse_args()

	if args.d:
		os.environ['RdsMonitor_DEBUG'] = '1'
		DEBUG = 1
	
	if DEBUG:
		print 'Get argv:'
		for argv, v in args._get_kwargs():
			print '%-10s:%-20s'%(argv, v)
			
	if not os.path.exists(args.f):
		print >>sys.stderr, "Config file %s not found. \nPlease use %s -f to special config file"%(args.f, sys.argv[0])
		sys.exit(1)

	if args.daemon:
		daemon(args.log if args.log else '/dev/null')
	
	monitor = RedisMonitor()
	monitor.run(args.f, args.duration, args.interval)
