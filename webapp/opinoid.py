#!/usr/bin/env python
#
# generic
import os

# tornado requirements
import tornado.httpserver
import tornado.ioloop
import tornado.auth
import tornado.web

# application db management class
import db

# geoip
import pygeoip
GEOIP = pygeoip.GeoIP(os.path.join(os.path.dirname(__file__), "GeoIP.dat"))

# regexp
from re import sub
from textile import textile_restricted

# tornado options
from tornado.options import define, options
define("db_host", default="localhost", help="DB host")
define("db_port", default="27017", help="DB port")
define("db_user", default="", help="DB user")
define("db_pass", default="", help="DB pass")


class ArticleModule(tornado.web.UIModule):
 def render(self, article):
  return self.render_string("modules/article.html", article=article)


class CommentModule(tornado.web.UIModule):
 def render(self, comment, cite=False):
  return self.render_string("modules/comment.html", comment=comment, cite=cite)


class UserModule(tornado.web.UIModule):
 def render(self, oid):
  return self.render_string("modules/user.html", oid=oid)


class AdModule(tornado.web.UIModule):
 def render(self, size):
  return self.render_string("modules/ad.html", size=size)


class PaginationModule(tornado.web.UIModule):
 def render(self, pd):
  return self.render_string("modules/pagination.html", pd=pd)


class BaseHandler(tornado.web.RequestHandler):
 @property
 def mongoworker(self):
  return db.MongoWorker(options.db_host, int(options.db_port), options.db_user, options.db_pass)

 def get_current_user(self):
  user_oid = self.get_secure_cookie("useroid")
  if user_oid:
   if self.mongoworker.get_user_by_oid(user_oid):
    return user_oid
   else:
    self.clear_all_cookies()
    return None
  else:
   return None


class GoogleHandler(BaseHandler, tornado.auth.GoogleMixin):
 @tornado.web.asynchronous
 def get(self):
  self.fromurl = self.get_argument("fromurl", default="/")
  if self.get_argument("openid.mode", False):
   self.get_authenticated_user(self.async_callback(self._on_auth))
   return
  self.authenticate_redirect()

 def _on_auth(self, user):
  if not user:
   raise tornado.web.HTTPError(500, "Google auth failed")
  opinoiduser = {}
  opinoiduser["first_name"] = user["first_name"]
  opinoiduser["last_name"] = user["last_name"]
  opinoiduser["email"] = user["email"]
  opinoiduser["provider"] = "google"
  user_oid = self.mongoworker.update_users_collection(opinoiduser)
  self.set_secure_cookie("useroid", user_oid)
  self.redirect(self.fromurl)


class FacebookHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
 @tornado.web.asynchronous
 def get(self):
  self.fromurl = self.get_argument("fromurl", default="/")
  redirect_uri = self.request.protocol + '://' + self.request.host + '/login/facebook'
  if self.get_argument("code", False):
   self.get_authenticated_user(redirect_uri, client_id=self.settings["facebook_api_key"], client_secret=self.settings["facebook_secret"], code=self.get_argument("code"), callback=self.async_callback(self._on_auth))
   return
  self.authorize_redirect(redirect_uri, client_id=self.settings["facebook_api_key"], extra_params={"scope": "email"})

 def _on_auth(self, user):
  if not user:
   raise tornado.web.HTTPError(500, "Facebook auth failed")
  print user
  opinoiduser = {}
  opinoiduser["first_name"] = user["first_name"]
  opinoiduser["last_name"] = user["last_name"]
  opinoiduser["email"] = user["email"]
  opinoiduser["provider"] = "facebook"
  user_oid = self.mongoworker.update_users_collection(opinoiduser)
  self.set_secure_cookie("useroid", user_oid)
  self.redirect(self.fromurl)


class LoginHandler(BaseHandler):
 def get(self):
  raise tornado.web.HTTPError(403)


class LogoutHandler(BaseHandler):
 def get(self):
  self.clear_all_cookies()
  self.redirect("/")


class CreditsHandler(BaseHandler):
 def get(self):
  self.render("credits.html")


class PrivacyHandler(BaseHandler):
 def get(self):
  self.render("privacy.html")


class ContactHandler(BaseHandler):
 def get(self):
  self.render("contact.html")


class CountryHandler(BaseHandler):
 def get(self, country=None):
  remoteip = self.request.remote_ip
  remotecountry = GEOIP.country_code_by_addr(remoteip)
  if not country:
   if remotecountry in self.mongoworker.get_countries():
    country = remotecountry
   else:
    country = "US"
  pd = self.get_argument("pd", "0")
  secsago = 86400
  if pd.isdigit() and int(pd) in range(1, 7):
   secsago = secsago + (int(pd) * 86400)
  else:
   pd = 0
  articles = self.mongoworker.get_articles_by_country(country, secsago)
  self.render("country.html", country=country, articles=articles, pd=pd)


class CommentsAJAXHandler(BaseHandler):
 def get(self, oid):
  comments = self.mongoworker.get_comments_by_article_oid(oid)
  self.render("ajax/comments.html", oid=oid, comments=comments)


class ArticleHandler(BaseHandler):
 def get(self, oid):
  article = self.mongoworker.get_article_by_oid(oid)
  self.render("article.html", oid=oid, article=article)


class SourceHandler(BaseHandler):
 def get(self, oid):
  pd = self.get_argument("pd", "0")
  secsago = 86400
  if pd.isdigit() and int(pd) in range(1, 7):
   secsago = secsago + (int(pd) * 86400)
  else:
   pd = 0
  articles = self.mongoworker.get_articles_by_source_oid(oid, secsago, also_same_title=True)
  self.render("source.html", oid=oid, articles=articles, pd=pd)


class UserHandler(BaseHandler):
 def get(self, oid):
  by = self.get_argument("by", "comments")
  user = self.mongoworker.get_user_by_oid(oid)
  comments = self.mongoworker.get_comments_by_user_oid(oid)
  votes = self.mongoworker.get_articles_by_user_oid(oid)
  self.render("user.html", oid=oid, user=user, comments=comments, votes=votes, by=by)


class CommentHandler(BaseHandler):
 @tornado.web.authenticated
 def post(self):
  parent_oid = self.get_argument("parent_oid")
  user_oid = self.get_current_user()
  text = self.get_argument("text")
  text = sub(r'<.*>', '', text)
  html = textile_restricted(text)
  html = sub(r'<p>', '', html)
  html = sub(r'</p>', '', html)
  retcode = self.mongoworker.post_comment_by_parent_oid(parent_oid, user_oid, html)
  self.write(retcode)
  self.finish()


class VoteHandler(BaseHandler):
 @tornado.web.authenticated
 def get(self):
  oid = self.get_argument("oid")
  user_oid = self.get_current_user()
  retcode = self.mongoworker.voteup_by_oid(oid, user_oid)
  self.write(retcode)
  self.finish()

handlers = [
 (r"/country/([\w]+)", CountryHandler),
 (r"/user/([\w]+)", UserHandler),
 (r"/article/([\w]+)", ArticleHandler),
 (r"/source/([\w]+)", SourceHandler),
 (r"/comments/ajax/([\w]+)", CommentsAJAXHandler),
 (r"/comment/add", CommentHandler),
 (r"/vote/add", VoteHandler),
 (r"/", CountryHandler),
 (r"/login", LoginHandler),
 (r"/login/google", GoogleHandler),
 (r"/login/facebook", FacebookHandler),
 (r"/logout", LogoutHandler),
 (r"/credits", CreditsHandler),
 (r"/privacy", PrivacyHandler),
 (r"/contact", ContactHandler),
]
settings = {
 "site_title": "Opinoid",
 "template_path": os.path.join(os.path.dirname(__file__), "templates"),
 "static_path": os.path.join(os.path.dirname(__file__), "static"),
 "login_url": "/login",
 "xsrf_cookies": True,
 "cookie_secret": "577a0cd2384e6d933ce10be00a535c04",
 "ui_modules": {"Article": ArticleModule, "Comment": CommentModule, "User": UserModule, "Ad": AdModule, "Pagination": PaginationModule},
 "autoescape": None,
 "facebook_api_key": "",
 "facebook_secret": "",
 "debug": False
}

application = tornado.web.Application(handlers, **settings)


def main():
 tornado.options.parse_command_line()
 http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
 address = "0.0.0.0"
 port = 8888
 http_server.listen(port, address=address)
 print "Listening on %s:%s" % (address, port)
 tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
 main()
