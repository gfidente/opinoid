#!/usr/bin/env python
#
# feed parser
from feedparser import parse

# regexp
from re import sub

# pymongo
from pymongo import Connection
from bson import objectid

# time management
from time import time, strftime
from calendar import timegm

# url parsing/extracting
from urlparse import urlparse
import tldextract

# logging
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# options
import argparse


def main(dbhost, dbport, dbuser, dbpass):
 wtin = int(time())
 logging.info("current time %s", wtin)
 connection = Connection(dbhost, dbport)
 db = connection.opinoid
 db.authenticate(dbuser, dbpass)
 populate(db, wtin)
 cleanup(db, wtin)
 logrun(db, wtin)
 connection.disconnect()


def populate(db, wtin):
 logging.info("STARTED populate")
 feeds = db.feeds
 articles = db.articles
 for feed in feeds.find():
  logging.info("working on %s", feed["url"])
  feed_oid = feed["_id"]
  logging.info("id %s", feed["_id"])
  feed_changes = {}

  # parsing
  feed_parsed = parse(feed["url"])
  valid_states = [200, 203, 301, 302, 307]
  if feed_parsed.status not in valid_states:
   logging.error("skipping %s, status %s", feed["url"], feed_parsed.status)
   continue

  # feed_title if not set (first time parsing)
  if "title" not in feed.keys():
   feed_url_parsed = urlparse(feed["url"])
   feed_url_extracted = tldextract.extract(feed_url_parsed.hostname)
   feed_domain = ".".join(feed_url_extracted[1:3])
   feed_changes["title"] = feed_domain
   logging.debug("feed title set to %s", feed_domain)

  # check if the feed has been updated after our last visit
  last_updated = int(feed["updated"]) if "updated" in feed.keys() else 0
  feed_updated = int(timegm(feed_parsed.feed["updated_parsed"])) if "updated_parsed" in feed_parsed.feed.keys() else 1
  feed_changes["updated"] = feed_updated
  if feed_parsed.feed.has_key("image"):
   feed_changes["image_href"] = feed_parsed.feed.image.href
  logging.debug("last_updated is now set to %s", last_updated)
  logging.debug("feed_updated is now set to %s", feed_updated)
  if feed_updated <= last_updated:
   logging.error("skipping %s, feed does not seem to have been updated after our last visit", feed["url"])
   continue

  # insert the actual entries if newer than last_updated
  added = 0
  skipped = 0
  for entry in feed_parsed.entries:
   entry_updated = int(timegm(entry["published_parsed"])) if "published_parsed" in entry.keys() else 1
   logging.debug("entry_updated is now set to %s", entry_updated)
   if entry_updated > last_updated:
    logging.debug("adding %s", entry.link)
    entry_title = sub(r'<.*>', '', entry.title)
    if entry_title.strip() == "":
      continue
    articles.insert({"title": entry_title, "link": entry.link, "updated": entry_updated, "updated_iso8601": strftime("%Y-%m-%dT%H:%M:%SZ", entry["published_parsed"]), "feed_oid": str(feed_oid), "score": 100, "score_updated": wtin, "comments": 0})
    added = added + 1
   else:
    logging.debug("skipping %s, entry should be already on db", entry.link)
    skipped = skipped + 1
  feeds.update({"url": feed["url"]}, {"$set": feed_changes})
  logging.info("entries received %s, skipped %s, added %s", len(feed_parsed.entries), skipped, added)


def logrun(db, wtin):
 logging.info("STARTED logrun")
 populate = db.populate
 populate.insert({"daterun": wtin, "full": True})
 logging.info("last full run at %s", wtin)


def cleanup(db, wtin):
 logging.info("STARTED cleanup")
 articles = db.articles
 comments = db.comments
 amonthago = wtin - 2678400
 logging.info("deleting articles older than %s", amonthago)
 aremoved = 0
 cremoved = 0
 for article in articles.find({"score": 100, "updated": {"$lt": amonthago}}):
  logging.debug("removing article %s", article["link"])
  article_oid_string = str(article["_id"])
  article_oid = objectid.ObjectId(article["_id"])
  articles.remove(article_oid)
  for comment in comments.find({"article_oid": article_oid_string}):
   comment_oid = objectid.ObjectId(comment["_id"])
   comments.remove(comment_oid)
   cremoved = cremoved + 1
  aremoved = aremoved + 1
 logging.info("articles deleted %s, comments %s", aremoved, cremoved)


if __name__ == "__main__":
 parser = argparse.ArgumentParser()
 parser.add_argument("--db_host", dest="dbhost", action='store', default="localhost", help="DB host")
 parser.add_argument("--db_port", dest="dbport", action='store', default=27017, help="DB host")
 parser.add_argument("--db_user", dest="dbuser", action='store', default="", help="DB host")
 parser.add_argument("--db_pass", dest="dbpass", action='store', default="", help="DB host")
 args = parser.parse_args()
 main(args.dbhost, int(args.dbport), args.dbuser, args.dbpass)
