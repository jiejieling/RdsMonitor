import tornado.web


class IndexController(tornado.web.RequestHandler):
	def get(self):
		self.redirect("/index.html")
		return 