from discord.ext import tasks, commands
from discord import Embed
import datetime
import arrow
from typing import List
from tzlocal import get_localzone
import requests
import datetime
import time
import urllib
import json
import cutlet
katsu = cutlet.Cutlet()
katsu.use_foreign_spelling = False
interested = ["🎤","歌","sing","karaoke","asmr","ku100","archive","アーカイブなし","3d","3 d", "万"]
hololive_schedule = {}
last_sync_unix = 0

def sync():
  global last_sync_unix
  if (last_sync_unix + 30 * 60) > int(time.time()):
    return
  last_sync_unix = int(time.time())
  global hololive_schedule
  raw_schedule = requests.get("https://hololive-api.marnixah.com/").json()
  streams = []
  for day in raw_schedule["schedule"]:
    date_month = day["date"].split("/")[0]
    date_day = day["date"].split("/")[1]
    for stream in day["schedules"]:
      stream_dict = {}
      title = get_youtube_title(stream["youtube_url"])
      
      if not any(term in title.lower() for term in interested):
        continue
      
      stream_dict["title"] = katsu.romaji(title)
      
      stream_dict["url"] = stream["youtube_url"]
      stream_dict["talent"] = katsu.romaji(stream["member"])

      time_arr = stream["time"].split(":")
      hour = int(time_arr[0])
      minute = int(time_arr[1])

      current_time = datetime.datetime.utcnow()
      year = current_time.year

      stream_dict["datetime"] = datetime.datetime(
        year, int(date_month), int(date_day), hour, minute
      ) - datetime.timedelta(hours=9)  # JST is 9 hours ahead of UTC
      
      streams.append(stream_dict)
  hololive_schedule = streams

def get_youtube_title(youtube_url):
    params = {"format": "json", "url": youtube_url}
    url = "https://www.youtube.com/oembed"
    query_string = urllib.parse.urlencode(params)
    url = url + "?" + query_string

    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )

    with urllib.request.urlopen(req) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
        return data['title']

@commands.command(name="hololive", aliases=["schedule","holoschedule"])
async def run(ctx):
  global hololive_schedule
  e = Embed(title="Hololive schedule")
  try:
    sync()
  except AttributeError:
    e.add_field(name="Error", value="There was an error with the hololive API")
    e.color = 0xFF0000
    await ctx.send(embed=e)

  e.color = 0x00FF00
  entries = []
  current_day = -1
  current_time = datetime.datetime.now()
  
  for stream in hololive_schedule:
    date: datetime.datetime = stream["datetime"]
    time = arrow.Arrow(date.year, date.month, date.day, date.hour, date.minute, date.second)
    
    if not current_day == date.day:
      current_day = date.day
      if not len(entries) == 0:
        entries.append("")
      diff = datetime.datetime(date.year, date.month, date.day, current_time.hour, current_time.minute, current_time.second) - current_time
      if diff.days < 0:
        entries.append("**today**")
      elif diff.days == 0:
        entries.append("**tomorrow**")
      else:
        entries.append("**in {} days".format(diff.days))
    offset_minutes = int(get_localzone().utcoffset(datetime.datetime.utcnow()).total_seconds() / 60)
    
    entries.append("**[{}]({})**".format(stream["title"], stream["url"]))
    entries.append(stream["talent"])
    entries.append("{}({})".format(time.humanize(), (stream["datetime"] + datetime.timedelta(minutes=offset_minutes)).strftime("%I:%M %p")))
      
  e.description = "\n".join(entries)
  await ctx.send(embed=e)

def setup(bot):
  bot.add_command(run)

def teardown(bot):
  global last_sync_unix
  global hololive_schedule
  last_sync_unix = 0
  hololive_schedule = {}