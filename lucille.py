import hipchat.config
from hipchat.room import Room
import json
import re
from httplib2 import Http
from urllib import urlencode
import random
import datetime
from dateutil import parser
import time
import urllib

hipchat.config.init_cfg('hipchat.cfg')

lucille_cfg_file = open('lucille.cfg')
lucille_cfg = json.load(lucille_cfg_file)
giphy_api_key = lucille_cfg.get("giphy_api_key",None)
hipchat_room = lucille_cfg.get("hipchat_room", None)

if giphy_api_key == None:
  print "missing giphy_api_key in cfg"
  exit()

if hipchat_room == None:
  print "missing hipchat_room in cfg"
  exit()


raw_hipchat_log=open('lucille.log')
try:
  hipchat_log = json.load(raw_hipchat_log)
except Exception:
  hipchat_log = {};
#print(url_log)
raw_hipchat_log.close()

digg_room = None
for r in Room.list():
  if r.name == "digg": #digg
    digg_room = r
    break

if digg_room == None:
  print "no room found for digg"
  exit()

GIPHY_REGEX = re.compile("\/giphy (.+)")

# http://help.hipchat.com/knowledgebase/articles/64359-running-a-hipchat-bot
while True:
  terms = []

  last_message_time = hipchat_log.get("last_message_time",0)
  most_recent_message_date = None

  try:
    recent_messages = Room.history(room_id=digg_room.room_id, date="recent")
  except Exception, e:
    print e
    time.sleep(20)
    continue

  for m in recent_messages:
    user = getattr(m, 'from')
    user_name = user.get('name')
    user_id = user.get('user_id',None)
    if user_id == "api" or user_name == "lucille":
      # print "user is api or lucille!"
      continue

    try:
      message = getattr(m, 'message')
      message_date_string = getattr(m, 'date')
      message_date = parser.parse(message_date_string)
      message_time = time.mktime(message_date.timetuple())
      # print time.mktime(message_date.timetuple())
      if message_time > last_message_time and message:
        term = GIPHY_REGEX.findall(message)
        if term:
          # print message_date
          # print last_message_time
          if most_recent_message_date:
            if most_recent_message_date > message_date:
              most_recent_message_date = message_date
          else:
            most_recent_message_date = message_date
          if message_time > last_message_time:
            terms.append(term[0])
    except AttributeError, e:
      print e
      pass

  # print terms
  # print "most_recent_message_date = %s" % most_recent_message_date
  if most_recent_message_date:
    most_recent_message_time = time.mktime(most_recent_message_date.timetuple())
    hipchat_log["last_message_time"] = most_recent_message_time
  # print hipchat_log
  # exit()

  gif_urls = []
  no_results = []

  for t in terms:
    encoded_t = urllib.quote_plus(t)
    print encoded_t
    url = "http://api.giphy.com/v1/gifs/search?q=%s&api_key=%s" % (encoded_t,giphy_api_key)
    h = Http()
    resp, content = h.request(url, "GET")
    # print resp
    # print content
    gif_list = json.loads(content)
    data = gif_list.get("data")
    count = len(data)
    if count == 0:
      # print "no results for %s" % encoded_t
      no_results.append(t)
      continue
    random_index = random.randrange(count)
    gif_dict = data[random_index]
    images = gif_dict.get("images",None)
    if images:
      original_image = images.get("original", None)
      if original_image:
        original_image_url = original_image.get("url",None)
        if original_image_url:
          gif_urls.append(original_image_url)

  # print gif_urls

  for url in gif_urls:
    print url
    # message_text = "%s: %s" % ()
    message = {'room_id': digg_room.room_id, 'from': 'lucille', 'message': url, 'message_format' : 'text', 'color' : 'green'}
    Room.message(**message)

  if len(no_results):
    no_results_string = ", ".join(no_results)
    message_text = "No results for: %s" % no_results_string
    message = {'room_id': digg_room.room_id, 'from': 'lucille', 'message': message_text, 'message_format' : 'text', 'color': 'gray'}
    Room.message(**message)


  with open('lucille.log', 'w') as outfile:
    json.dump(hipchat_log, outfile)

  time.sleep(5)

