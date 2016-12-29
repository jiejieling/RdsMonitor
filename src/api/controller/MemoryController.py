from BaseController import BaseController
import dateutil.parser
import datetime, time


class MemoryController(BaseController):

	def get(self):
		server = self.get_argument("server")
		from_date = self.get_argument("from", None)
		to_date = self.get_argument("to", None)

		return_data = dict(data=[],
						   timestamp=datetime.datetime.now().isoformat())

		if not from_date or not to_date:
			end = int(time.time())
			start = end - int(time.time() - 60)
		else:
			try:
				time.ctime(int(from_date))
				time.ctime(int(to_date))
			except:
				self.write(return_data)
				return
			
			start = int(from_date)
			end   = int(to_date)

		# TODO: These variables aren't currently used; should they be removed?
		prev_max=0
		prev_current=0
		counter=0

		for data in self.stats_provider.get_memory_info(server, start, end):
			return_data['data'].append([data[0], data[1], data[2]])

		self.write(return_data)

