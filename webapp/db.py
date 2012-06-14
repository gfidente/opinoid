# pymongo
from pymongo import Connection, ASCENDING, DESCENDING
from bson import objectid

# time management
from time import time, gmtime, strftime

# hotness
from math import exp

# pymongo mapreduce
from bson.code import Code

# EU Member States (exluding countries added in 2004 and later) + US +  Canada
countries = ["US", "CDN", "UK", "DE", "FR", "IT", "ES", "NL", "GR", "SE", "DK", "FI", "IE", "PT", "BE", "A"]
categories = ["frontpage", "economy", "technology", "culture", "sport"]


class MongoWorker:
 def __init__(self, dbhost, dbport, dbuser, dbpass):
  mongo = Connection(dbhost, dbport, max_pool_size=8)
  self.db = mongo.opinoid
  self.db.authenticate(dbuser, dbpass)

 def __get_hotness(self, time, score, score_update):
  # implements N(t) = N(0) * e ^ (-t/theta)
  # theta = 28800, time needed to reduce at 63%
  timedelta = time - score_update
  hotness = score * exp(-timedelta / 28800)
  # hotness = score * exp(-timedelta/3600)
  return hotness

 def get_last_full_run(self):
  populate = self.db.populate
  entries = []
  for entry in populate.find({"full": True}).sort("daterun", DESCENDING).limit(1):
   entries.append(entry)
  daterun = entries[0]["daterun"]
  return strftime("%Y-%m-%dT%H:%M:%SZ", gmtime(daterun))

 def get_categories(self):
  return categories

 def get_categories_by_feed_title(self, title):
  feeds = self.db.feeds
  categories = []
  for entry in feeds.find({"title": title}):
   categories.append(entry["category"])
  return categories

 def get_countries(self):
  countries.sort()
  return countries

 def get_feeds_by_country(self, country, unique_titles=False):
  feeds = self.db.feeds
  entries = []
  seen_titles = []
  for entry in feeds.find({"country": country}):
   if not unique_titles:
    entries.append(entry)
   else:
    if entry["title"] not in seen_titles:
     seen_titles.append(entry["title"])
     entries.append(entry)
  return entries

 def get_feed_by_oid(self, oid):
  feeds = self.db.feeds
  oid = objectid.ObjectId(oid)
  entry = feeds.find_one(oid)
  return entry

 def get_articles_by_country(self, country, lowest=86400):
  articles = self.db.articles
  feed_oids = []
  for feed in self.get_feeds_by_country(country):
   feed_oids.append(str(feed["_id"]))
  entries = []
  wtin = int(time())
  lowest = wtin - lowest
  highest = lowest + 86400
  for entry in articles.find({
                              "feed_oid": {"$in": feed_oids},
                              "$where": "this.updated >= " + str(lowest) + " && this.updated <= " + str(highest)
                             }).sort("updated", DESCENDING):
   entry["hotness"] = self.__get_hotness(wtin, entry["score"], entry["score_updated"])
   entries.append(entry)
  return entries

 def get_articles_by_source_oid(self, oid, lowest=86400, also_same_title=False):
  samesource_oids = []
  if also_same_title:
   feed = self.get_feed_by_oid(oid)
   feeds = self.db.feeds
   for samesource in feeds.find({"title": feed["title"]}):
    samesource_oids.append(str(samesource["_id"]))
  else:
   samesource_oids.append(oid)
  articles = self.db.articles
  entries = []
  wtin = int(time())
  lowest = wtin - lowest
  highest = lowest + 86400
  for entry in articles.find({
                              "feed_oid": {"$in": samesource_oids},
                              "$where": "this.updated >= " + str(lowest) + " && this.updated <= " + str(highest)
                             }).sort("updated", DESCENDING):
   entry["hotness"] = self.__get_hotness(wtin, entry["score"], entry["score_updated"])
   entries.append(entry)
  return entries

 def get_article_by_oid(self, oid):
  articles = self.db.articles
  oid = objectid.ObjectId(oid)
  entry = articles.find_one(oid)
  wtin = int(time())
  entry["hotness"] = self.__get_hotness(wtin, entry["score"], entry["score_updated"])
  return entry

 def get_comments_by_article_oid(self, oid):
  comments = self.db.comments
  entries = []
  for entry in comments.find({"article_oid": oid}).sort("updated", DESCENDING):
   entries.append(entry)
  threaded = self.__thread_comments_with_replies(oid, entries)
  return threaded

 def get_comment_by_oid(self, oid):
  comments = self.db.comments
  oid = objectid.ObjectId(oid)
  entry = comments.find_one(oid)
  wtin = int(time())
  if entry:
   entry = self.__add_comment_details(wtin, entry)
  return entry

 def __add_comment_details(self, wtin, entry):
  entry["hotness"] = self.__get_hotness(wtin, entry["score"], entry["score_updated"])
  user = self.get_user_by_oid(entry["submitter"])
  entry["user_name"] = user["first_name"] + " " + user["last_name"]
  if "profile_url" in user.keys():
   entry["user_profile_url"] = user["profile_url"]
  return entry

 def __thread_comments_with_replies(self, parent_oid, collection):
  entries = []
  wtin = int(time())
  for entry in collection:
   if entry["parent_oid"] == parent_oid:
    entry = self.__add_comment_details(wtin, entry)
    entry["replies"] = self.__thread_comments_with_replies(str(entry["_id"]), collection)
    entries.append(entry)
  return entries

 def post_comment_by_parent_oid(self, parent_oid, user_oid, text):
  comments = self.db.comments
  article_oid = ""
  parent = self.get_comment_by_oid(parent_oid)
  if parent:
   article_oid = parent["article_oid"]
  else:
   parent = self.get_article_by_oid(parent_oid)
   if parent:
    article_oid = str(parent["_id"])
   else:
    return "nooid"
  wtin = int(time())
  comments.insert({"submitter": user_oid, "updated": wtin, "updated_iso8601": strftime("%Y-%m-%dT%H:%M:%SZ", gmtime(wtin)), "text": text, "score": 100, "score_updated": wtin, "parent_oid": parent_oid, "article_oid": article_oid})
  self.update_comments_count_by_article_oid(article_oid)
  self.voteup_by_oid(article_oid, user_oid)
  return article_oid

 def update_comments_count_by_article_oid(self, oid):
  articles = self.db.articles
  oid = objectid.ObjectId(oid)
  article = articles.find_one(oid)
  articles.update(article, {"$inc": {"comments": 1}})

 def voteup_by_oid(self, oid, user_oid):
  objtype = ""
  obj = self.get_comment_by_oid(oid)
  if obj:
   objtype = "comment"
   self.__update_score_by_oid(oid, user_oid, True)
   self.__update_score_by_oid(obj["article_oid"], user_oid, False)
  else:
   obj = self.get_article_by_oid(oid)
   if obj:
    objtype = "article"
    self.__update_score_by_oid(oid, user_oid, False)
   else:
    objtype = "nooid"
  return objtype

 def __update_score_by_oid(self, oid, user_oid, iscomment):
  if iscomment:
   entries = self.db.comments
  else:
   entries = self.db.articles
  oid = objectid.ObjectId(oid)
  entry = entries.find_one(oid)
  if "watchers" not in entry.keys() or user_oid not in entry["watchers"]:
   entries.update(entry, {"$addToSet": {"watchers": user_oid}, "$set": {"score": entry["score"] + 10}})

 def update_users_collection(self, user):
  wtin = int(time())
  users = self.db.users
  userondb = None
  if user["provider"] == "google":
   userondb = users.find_one({"email": user["email"]})
  elif user["provider"] == "facebook":
   userondb = users.find_one({"user_profile_url": user["profile_url"]})
  if userondb:
   userondb["lastlogin"] = wtin
   users.save(userondb)
   userid = userondb["_id"]
  else:
   user["lastlogin"] = wtin
   userid = users.insert(user, manipulate=True)
  return unicode(userid)

 def get_user_by_oid(self, oid):
  users = self.db.users
  oid = objectid.ObjectId(oid)
  entry = users.find_one(oid)
  return entry

 def get_numposts_by_user_oid(self, oid):
  comments = self.db.comments
  cursor = comments.find({"submitter": oid})
  numentries = cursor.count()
  return numentries

 def get_points_by_user_oid(self, oid):
  comments = self.db.comments
  points = 0
  for entry in comments.find({"submitter": oid, "score": {"$gt": 100}}):
   s = entry["score"]
   s = s / 10 - 10
   points = points + s
  return points

 def get_comments_by_user_oid(self, oid):
  comments = self.db.comments
  entries = []
  wtin = int(time())
  for entry in comments.find({"submitter": oid}).sort("updated", DESCENDING):
   entry = self.__add_comment_details(wtin, entry)
   entries.append(entry)
  return entries

 def get_articles_by_user_oid(self, oid):
  articles = self.db.articles
  entries = []
  wtin = int(time())
  for entry in articles.find({"watchers": oid}).sort("updated", DESCENDING):
   entry["hotness"] = self.__get_hotness(wtin, entry["score"], entry["score_updated"])
   entries.append(entry)
  return entries

 def get_mostliked_by_user_oid(self, oid):
  articles = self.db.articles
  map = Code("function() {"
             "  emit(this.feed_oid, 1);"
             "}")
  reduce = Code("function (key, values) {"
                "  var total = 0;"
                "  for (var i = 0; i < values.length; i++) {"
                "    total += values[i];"
                "  }"
                "  return total;"
                "}")
  results = articles.map_reduce(map, reduce, "mroutput", query={"watchers": oid})
  mostliked = {}
  if results:
   for line in results:
    feed = self.get_feed_by_oid(line["_id"])
    mostliked[feed["title"]] = line["value"]
  return mostliked
