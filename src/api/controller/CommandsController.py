from BaseController import BaseController
import time
from datetime import datetime


class CommandsController(BaseController):

	def get(self):
		"""Serves a GET request.
		"""
		return_data = dict(data=[], timestamp=datetime.now().isoformat())

		server = self.get_argument("server")
		from_date = self.get_argument("from", None)
		to_date = self.get_argument("to", None)

		if not from_date or not to_date:
			end = int(time.time())
			start = end - int(time.time() - 120)
		else:
			try:
				time.ctime(int(from_date))
				time.ctime(int(to_date))
			except:
				self.write(return_data)
				return
			
			start = int(from_date)
			end   = int(to_date)


		stats = self.stats_provider.get_command_stats(server, start, end)

		for data in stats:
			return_data['data'].append([data[0], data[1]])

		self.write(return_data)
