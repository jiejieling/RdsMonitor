import os, sys
from api.util.settings import settings
import sqliteprovider
import redisprovider



# TODO: Confirm there's not some implementation detail I've missed, then
# ditch the classes here.
class RedisLiveDataProvider(object):
	def __init__(self):
		self.DEBUG = os.environ.get('RdsMonitor_DEBUG', 0)
		
	def get_provider(self):
		"""Returns a data provider based on the settings file.

		Valid providers are currently Redis and SQLite.
		"""
		data_store_type = settings().get_data_store_type()

		# FIXME: Should use a global variable for "redis" here.
		if data_store_type == "redis":
			return redisprovider.RedisStatsProvider()
		elif data_store_type == "sqlite":
			return sqliteprovider.RedisStatsProvider()
		else:
			if self.DEBUG:
				print >> sys.stderr, 'Data store type %s is invalid, type only support in (redis, sqlite)'%data_store_type
			return ''