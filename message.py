# -*- coding: utf-8 -*-

# Nemubot is a modulable IRC bot, built around XML configuration files.
# Copyright (C) 2012  Mercier Pierre-Olivier
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import re
import shlex
import time

import credits
from credits import Credits
from response import Response
import xmlparser

CREDITS = {}
filename = ""

def load(config_file):
  global CREDITS, filename
  CREDITS = dict()
  filename = config_file
  credits.BANLIST = xmlparser.parse_file(filename)

def save():
  global filename
  credits.BANLIST.save(filename)

mgx = re.compile(b'''^(?:@(?P<tags>[^ ]+)\ )?
                      (?::(?P<prefix>
                         (?P<nick>[a-zA-Z][^!@ ]*)
                         (?: !(?P<user>[^@ ]+))?
                         (?:@(?P<host>[^ ]+))?
                      )\ )?
                      (?P<command>(?:[a-zA-Z]+|[0-9]{3}))
                      (?P<params>(?:\ [^:][^ ]*)*)(?:\ :(?P<trailing>.*))?
                 $''', re.X)

class Message:
  def __init__(self, raw_line, timestamp, private = False):
    self.raw = raw_line.rstrip() # remove trailing crlf
    self.tags = { 'time': timestamp }
    self.params = list()

    p = mgx.match(raw_line.rstrip())

    # Parse tags if exists: @aaa=bbb;ccc;example.com/ddd=eee
    if p.group("tags"):
      for tgs in p.group("tags").decode().split(';'):
        tag = tgs.split('=')
        if len(tag) > 1:
          self.add_tag(tag[0], tag[1])
        else:
          self.add_tag(tag[0])

    # Parse prefix if exists: :nick!user@host.com
    self.prefix = self.decode(p.group("prefix"))
    self.nick   = self.decode(p.group("nick"))
    self.user   = self.decode(p.group("user"))
    self.host   = self.decode(p.group("host"))

    # Parse command
    self.cmd = p.group("command").decode()

    # Parse params
    if p.group("params"):
      for param in p.group("params").strip().split(b' '):
        self.params.append(param)

    if p.group("trailing"):
      self.params.append(p.group("trailing"))

    # Special commands
    if self.cmd == 'PRIVMSG':
      self.receivers = self.params[0].decode().split(',')

      # If CTCP, remove 0x01
      if len(self.params[1]) > 1 and (self.params[1][0] == 0x01 or self.params[1][1] == 0x01):
        self.is_ctcp = True
        self.text = self.decode(self.params[1][1:len(self.params[1])-1])
      else:
        self.is_ctcp = False
        self.text = self.decode(self.params[1])

      # Split content by words
      try:
          self.cmds = shlex.split(self.text)
      except ValueError:
          self.cmds = self.text.split(' ')

    elif self.cmd == '353': # RPL_NAMREPLY
      self.receivers = [ self.params[0].decode() ]
      self.nicks = self.params[1].decode().split(" ")

    elif self.cmd == '332':
      self.receivers = [ self.params[0].decode() ]
      self.topic = self.params[1].decode().split(" ")

    else:
      for i in range(0, len(self.params)-1):
        self.params[i] = self.decode(self.params[i])

    print(self)


  def add_tag(self, key, value=None):
    """Add an IRCv3.2 Message Tags"""
    # Treat special tags
    if key == "time":
      value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    # Store tag
    self.tags[key] = value


  def decode(self, s):
    """Decode the content string usign a specific encoding"""
    if isinstance(s, bytes):
      try:
        s = s.decode()
      except UnicodeDecodeError:
        #TODO: use encoding from config file
        s = s.decode('utf-8', 'replace')
    return s


  def __str__(self):
    return "Message " + str(self.__dict__)


  def authorize_DEPRECATED(self):
      """Is nemubot listening for the sender on this channel?"""
      # TODO: deprecated
      if self.srv.isDCC(self.sender):
          return True
      elif self.realname not in CREDITS:
          CREDITS[self.realname] = Credits(self.realname)
      elif self.content[0] == '`':
          return True
      elif not CREDITS[self.realname].ask():
          return False
      return self.srv.accepted_channel(self.channel)

##############################
#                            #
#   Extraction/Format text   #
#                            #
##############################

  def just_countdown (self, delta, resolution = 5):
    sec = delta.seconds
    hours, remainder = divmod(sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    an = int(delta.days / 365.25)
    days = delta.days % 365.25

    sentence = ""
    force = False

    if resolution > 0 and (force or an > 0):
      force = True
      sentence += " %i an"%(an)

      if an > 1:
        sentence += "s"
      if resolution > 2:
        sentence += ","
      elif resolution > 1:
        sentence += " et"

    if resolution > 1 and (force or days > 0):
      force = True
      sentence += " %i jour"%(days)

      if days > 1:
        sentence += "s"
      if resolution > 3:
        sentence += ","
      elif resolution > 2:
        sentence += " et"

    if resolution > 2 and (force or hours > 0):
      force = True
      sentence += " %i heure"%(hours)
      if hours > 1:
        sentence += "s"
      if resolution > 4:
        sentence += ","
      elif resolution > 3:
        sentence += " et"

    if resolution > 3 and (force or minutes > 0):
      force = True
      sentence += " %i minute"%(minutes)
      if minutes > 1:
        sentence += "s"
      if resolution > 4:
        sentence += " et"

    if resolution > 4 and (force or seconds > 0):
      force = True
      sentence += " %i seconde"%(seconds)
      if seconds > 1:
        sentence += "s"
    return sentence[1:]


  def countdown_format (self, date, msg_before, msg_after, timezone = None):
    """Replace in a text %s by a sentence incidated the remaining time before/after an event"""
    if timezone != None:
      os.environ['TZ'] = timezone
      time.tzset()

    #Calculate time before the date
    if datetime.now() > date:
        sentence_c = msg_after
        delta = datetime.now() - date
    else:
        sentence_c = msg_before
        delta = date - datetime.now()

    if timezone != None:
      os.environ['TZ'] = "Europe/Paris"

    return sentence_c % self.just_countdown(delta)


  def extractDate (self):
    """Parse a message to extract a time and date"""
    msgl = self.content.lower ()
    result = re.match("^[^0-9]+(([0-9]{1,4})[^0-9]+([0-9]{1,2}|janvier|january|fevrier|février|february|mars|march|avril|april|mai|maï|may|juin|juni|juillet|july|jully|august|aout|août|septembre|september|october|octobre|oktober|novembre|november|decembre|décembre|december)([^0-9]+([0-9]{1,4}))?)[^0-9]+(([0-9]{1,2})[^0-9]*[h':]([^0-9]*([0-9]{1,2})([^0-9]*[m\":][^0-9]*([0-9]{1,2}))?)?)?.*$", msgl + " TXT")
    if result is not None:
      day = result.group(2)
      if len(day) == 4:
        year = day
        day = 0
      month = result.group(3)
      if month == "janvier" or month == "january" or month == "januar":
        month = 1
      elif month == "fevrier" or month == "février" or month == "february":
        month = 2
      elif month == "mars" or month == "march":
        month = 3
      elif month == "avril" or month == "april":
        month = 4
      elif month == "mai" or month == "may" or month == "maï":
        month = 5
      elif month == "juin" or month == "juni" or month == "junni":
        month = 6
      elif month == "juillet" or month == "jully" or month == "july":
        month = 7
      elif month == "aout" or month == "août" or month == "august":
        month = 8
      elif month == "september" or month == "septembre":
        month = 9
      elif month == "october" or month == "october" or month == "oktober":
        month = 10
      elif month == "november" or month == "novembre":
        month = 11
      elif month == "december" or month == "decembre" or month == "décembre":
        month = 12

      if day == 0:
        day = result.group(5)
      else:
        year = result.group(5)

      hour = result.group(7)
      minute = result.group(9)
      second = result.group(11)

      print ("Chaîne reconnue : %s/%s/%s %s:%s:%s"%(day, month, year, hour, minute, second))
      if year == None:
        year = date.today().year
      if hour == None:
        hour = 0
      if minute == None:
        minute = 0
      if second == None:
        second = 1
      else:
        second = int (second) + 1
        if second > 59:
          minute = int (minute) + 1
          second = 0

      return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    else:
      return None
