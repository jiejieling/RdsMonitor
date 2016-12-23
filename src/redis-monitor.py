#! /usr/bin/env python
#-*-coding:utf8-*-

import os, sys, time, datetime
from api.util.settings import settings
from dataprovider.dataprovider import RedisLiveDataProvider
from threading import Timer
import redis 
import threading
import traceback
import argparse

DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)

class Monitor(object):
	"""Monitors a given Redis server using the MONITOR command.
	"""

	def __init__(self, connection_pool):
		"""Initializes the Monitor class.

		Args:
			connection_pool (redis.ConnectionPool): Connection pool for the \
					Redis server to monitor.
		"""
		self.connection_pool = connection_pool
		self.connection = None

	def __del__(self):
		try:
			self.reset()
		except:
			pass

	def reset(self):
		"""If we have a connection, release it back to the connection pool.
		"""
		if self.connection:
			self.connection_pool.release(self.connection)
			self.connection = None

	def monitor(self):
		"""Kicks off the monitoring process and returns a generator to read the
		response stream.
		"""
		if self.connection is None:
			self.connection = self.connection_pool.get_connection('monitor', None)
		self.connection.send_command("monitor")
		return self.listen()

	def parse_response(self):
		"""Parses the most recent responses from the current connection.
		"""
		return self.connection.read_response()

	def listen(self):
		"""A generator which yields responses from the MONITOR command.
		"""
		while True:
			yield self.parse_response()

class MonitorThread(threading.Thread):
	"""Runs a thread to execute the MONITOR command against a given Redis server
	and store the resulting aggregated statistics in the configured stats
	provider.
	"""

	def __init__(self, server, port, password=None):
		"""Initializes a MontitorThread.

		Args:
			server (str): The host name or IP of the Redis server to monitor.
			port (int): The port to contact the Redis server on.

		Kwargs:
			password (str): The password to access the Redis host. Default: None
		"""
		super(MonitorThread, self).__init__()
		self.server = server
		self.port = port
		self.password = password
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
		"""Runs the thread.
		"""
		stats_provider = RedisLiveDataProvider.get_provider()
		pool = redis.ConnectionPool(host=self.server, port=self.port, db=0,
									password=self.password)
		monitor = Monitor(pool)
		commands = monitor.monitor()

		for command in commands:
			try:
				parts = command.split(" ")

				if len(parts) == 1:
					continue

				epoch = float(parts[0].strip())
				timestamp = datetime.datetime.fromtimestamp(epoch)

				# Strip '(db N)' and '[N x.x.x.x:xx]' out of the monitor str
				if (parts[1] == "(db") or (parts[1][0] == "["):
					parts = [parts[0]] + parts[3:]

				command = parts[1].replace('"', '').upper()

				if len(parts) > 2:
					keyname = parts[2].replace('"', '').strip()
				else:
					keyname = None

				if len(parts) > 3:
					# TODO: This is probably more efficient as a list
					# comprehension wrapped in " ".join()
					arguments = ""
					for x in xrange(3, len(parts)):
						arguments += " " + parts[x].replace('"', '')
					arguments = arguments.strip()
				else:
					arguments = None

				if not command == 'INFO' and not command == 'MONITOR':
					stats_provider.save_monitor_command(self.id, 
														timestamp, 
														command, 
														str(keyname), 
														str(arguments))

			except Exception, e:
				tb = traceback.format_exc()
				print "==============================\n"
				print datetime.datetime.now()
				print tb
				print command
				print "==============================\n"

			if self.stopped():
				break

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
		stats_provider = RedisLiveDataProvider.get_provider()
		if not stats_provider:
			print >>sys.stderr, 'Get data provider error'
			sys.exit(4)
	
		try:
			redis_client = redis.StrictRedis(host=self.server, port=self.port, db=0,
											password=self.password)
		except Exception, e:
			print >>sys.stderr, 'Connect to Redis %s:%i err: %s'%(self.server, self.port, e)
			sys.exit(3)
	
		# process the results from redis
		num = 10
		while not self.stopped():
			if num >= self.interval:
				num = 1
				redis_info = redis_client.info()
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
