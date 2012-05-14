# coding=utf-8

import re
import sys
from datetime import timedelta
from datetime import datetime
from datetime import date
import time
import threading
from xml.dom.minidom import parse
from xml.dom.minidom import parseString
from xml.dom.minidom import getDOMImplementation

filename = ""
EVENTS = {}
STREND = {}
threadManager = None
newStrendEvt = threading.Event()

class Manager(threading.Thread):
  def __init__(self, servers):
    self.servers = servers
    self.stop = False
    threading.Thread.__init__(self)

  def run(self):
    global STREND
    while not self.stop:
      newStrendEvt.clear()
      closer = None
      #Gets the closer event
      for evt in STREND.keys():
        if ((closer is None or closer.end is None) or (STREND[evt].end is not None and STREND[evt].end < closer.end)) and STREND[evt].end is not None and STREND[evt].end > datetime.now():
          closer = STREND[evt]
      if closer is not None and closer.end is not None:
        #print ("Closer: %s à %s"%(closer.name, closer.end))
        timeleft = (closer.end - datetime.now()).seconds
        timer = threading.Timer(timeleft, closer.alertEnd, (self.servers,))
        timer.start()
        #print ("Start timer (%ds)"%timeleft)

      newStrendEvt.wait()

      if closer is not None and closer.end is not None and closer.end > datetime.now():
        timer.cancel()

def launch (servers):
  global threadManager
  stop()
  threadManager = Manager(servers)
  threadManager.start()

def stop ():
  if threadManager is not None:
    threadManager.stop = True
    newStrendEvt.set()

class Strend:
  def __init__(self, item):
    if item is not None:
      self.name = item.getAttribute("name")
      self.start = datetime.fromtimestamp (time.mktime (time.strptime (item.getAttribute("start")[:19], "%Y-%m-%d %H:%M:%S")))
      self.proprio = item.getAttribute("proprio")
      self.server = item.getAttribute("server")
      self.channel = item.getAttribute("channel")
      if item.getAttribute("end") is not None and item.getAttribute("end") != "":
        try:
          self.end = datetime.fromtimestamp (time.mktime (time.strptime (item.getAttribute("end")[:19], "%Y-%m-%d %H:%M:%S")))
        except:
          self.end = None
      else:
        self.end = None
    else:
      self.start = datetime.now()
      self.end = None

  def alertEnd(self, SRVS):
    for server in SRVS.keys():
      if server == self.server:
        if self.channel == SRVS[server].nick:
          SRVS[server].send_msg_usr(self.proprio, "%s: %s arrivé à échéance."%(self.proprio, self.name))
        else:
          SRVS[server].send_msg(self.channel, "%s: %s arrivé à échéance."%(self.proprio, self.name))
    del STREND[self.name]
    newStrendEvt.set()

def xmlparse(node):
  """Parse the given node and add events to the global list."""
  for item in node.getElementsByTagName("strend"):
    STREND[item.getAttribute("name")] = Strend(item)

  for item in node.getElementsByTagName("event"):
    if (item.hasAttribute("year")):
      year = int(item.getAttribute("year"))
    else:
      year = 0
    if (item.hasAttribute("month")):
      month = int(item.getAttribute("month"))
    else:
      month = 0
    if (item.hasAttribute("day")):
      day = int(item.getAttribute("day"))
    else:
      day = 0
    if (item.hasAttribute("hour")):
      hour = int(item.getAttribute("hour"))
    else:
      hour = 0
    if (item.hasAttribute("minute")):
      minute = int(item.getAttribute("minute"))
    else:
      minute = 0
    if (item.hasAttribute("second")):
      second = int(item.getAttribute("second"))
    else:
      second = 0

    if year == month == day == hour == minute == second == 0:
      EVENTS[item.getAttribute("name")] = (None, item.getAttribute("before_after"), None)
    else:
      EVENTS[item.getAttribute("name")] = (datetime(year, month, day, hour, minute, second),item.getAttribute("msg_before"), item.getAttribute("msg_after"))


def load_module(datas_path):
  """Load this module"""
  global EVENTS, STREND, filename
  EVENTS = {}
  STREND = {}
  filename = datas_path + "/events.xml"

  sys.stdout.write ("Loading events ... ")
  dom = parse(filename)
  xmlparse (dom.getElementsByTagName('events')[0])
  print ("done (%d loaded)" % len(EVENTS))


def save_module():
  """Save the dates"""
  global filename
  sys.stdout.write ("Saving events ... ")

  impl = getDOMImplementation()
  newdoc = impl.createDocument(None, 'events', None)
  top = newdoc.documentElement

  for name in STREND.keys():
    iend = ""
    if STREND[name].end is not None:
      iend = ' end="%s"'%STREND[name].end
    item = parseString ('<strend name="%s" start="%s" proprio="%s" server="%s" channel="%s"%s />' % (name, STREND[name].start, STREND[name].proprio, STREND[name].server, STREND[name].channel, iend)).documentElement
    top.appendChild(item);

  for name in EVENTS.keys():
    (day, msg_before, msg_after) = EVENTS[name]
    bonus=""
    if day is None:
      item = parseString ('<event name="%s" msg_before="%s" />' % (name, msg_before)).documentElement
    else:
      if day.hour != 0:
        bonus += 'hour="%s" ' % day.hour
      if day.minute != 0:
        bonus += 'minute="%s" ' % day.minute
      if day.second != 1:
        bonus += 'second="%s" ' % day.second
      item = parseString ('<event name="%s" year="%d" month="%d" day="%d" %s msg_after="%s" msg_before="%s" />' % (name, day.year, day.month, day.day, bonus, msg_after, msg_before)).documentElement
    top.appendChild(item);

  with open(filename, "w") as f:
    newdoc.writexml (f)
  print ("done")


def help_tiny ():
  """Line inserted in the response to the command !help"""
  return "events manager"

def help_full ():
  return "This module store a lot of events: ny, we, vacs, " + (", ".join(EVENTS.keys())) + "\n!eventslist: gets list of timer\n!start /something/: launch a timer"


def parseanswer(msg):
  global STREND
  if msg.cmd[0] == "we" or msg.cmd[0] == "week-end" or msg.cmd[0] == "weekend":
    ndate = datetime.today() + timedelta(5 - datetime.today().weekday())
    ndate = datetime(ndate.year, ndate.month, ndate.day, 0, 0, 1)
    msg.send_chn (
      msg.countdown_format (ndate,
                            "Il reste %s avant le week-end, courrage ;)",
                            "Youhou, on est en week-end depuis %s."))
    return True
  elif msg.cmd[0] == "new-year" or msg.cmd[0] == "newyear" or msg.cmd[0] == "ny":
    msg.send_chn (
      msg.countdown_format (datetime(datetime.today().year + 1, 1, 1, 0, 0, 1),
                            "Il reste %s avant la nouvelle année.",
                            "Nous faisons déjà la fête depuis %s !"))
    return True
  elif msg.cmd[0] == "vacances" or msg.cmd[0] == "vacs" or msg.cmd[0] == "holiday" or msg.cmd[0] == "holidays":
    msg.send_chn (
      msg.countdown_format (datetime(2012, 7, 30, 18, 0, 1),
                            "Il reste %s avant les vacances :)",
                            "Profitons, c'est les vacances depuis %s."))
    return True
  elif msg.cmd[0] == "start" and len(msg.cmd) > 1:
    if msg.cmd[1] not in STREND:
      STREND[msg.cmd[1]] = Strend(None)
      STREND[msg.cmd[1]].server = msg.srv.id
      STREND[msg.cmd[1]].channel = msg.channel
      STREND[msg.cmd[1]].proprio = msg.sender
      STREND[msg.cmd[1]].name = msg.cmd[1]
      if len(msg.cmd) > 2:
        result = re.match("([0-9]+)([smhdjSMHDJ])?", msg.cmd[2])
        if result is not None:
          try:
            if result.group(2) is not None and (result.group(2) == "m" or result.group(2) == "M"):
              STREND[msg.cmd[1]].end = datetime.now() + timedelta(minutes=int(result.group(1)))
            elif result.group(2) is not None and (result.group(2) == "h" or result.group(2) == "H"):
              STREND[msg.cmd[1]].end = datetime.now() + timedelta(hours=int(result.group(1)))
            elif result.group(2) is not None and (result.group(2) == "d" or result.group(2) == "D" or result.group(2) == "j" or result.group(2) == "J"):
              STREND[msg.cmd[1]].end = datetime.now() + timedelta(days=int(result.group(1)))
            else:
              STREND[msg.cmd[1]].end = datetime.now() + timedelta(seconds=int(result.group(1)))
            newStrendEvt.set()
            msg.send_snd ("%s commencé le %s et se terminera le %s."% (msg.cmd[1], datetime.now(), STREND[msg.cmd[1]].end))
          except:
            msg.send_snd ("Impossible de définir la fin de %s."% (msg.cmd[1]))
            msg.send_snd ("%s commencé le %s."% (msg.cmd[1], datetime.now()))
        else:
          msg.send_snd ("%s commencé le %s"% (msg.cmd[1], datetime.now()))
    else:
      msg.send_snd ("%s existe déjà."% (msg.cmd[1]))

  elif (msg.cmd[0] == "end" or msg.cmd[0] == "forceend") and len(msg.cmd) > 1:
    if msg.cmd[1] in STREND:
      msg.send_chn ("%s a duré %s." % (msg.cmd[1], msg.just_countdown(datetime.now () - STREND[msg.cmd[1]].start)))
      if STREND[msg.cmd[1]].proprio == msg.sender or (msg.cmd[0] == "forceend" and msg.sender == msg.srv.owner):
        del STREND[msg.cmd[1]]
        newStrendEvt.set()
      else:
        msg.send_snd ("Vous ne pouvez pas terminer le compteur %s, créé par %s."% (msg.cmd[1], STREND[msg.cmd[1]].proprio))
    else:
      msg.send_snd ("%s n'est pas un compteur connu."% (msg.cmd[1]))

  elif msg.cmd[0] == "eventslist" or msg.cmd[0] == "eventlist" or msg.cmd[0] == "eventsliste" or msg.cmd[0] == "eventliste":
    msg.send_snd ("Compteurs connus : %s." % ", ".join(STREND.keys()))
  elif msg.cmd[0] in STREND:
    msg.send_chn ("%s commencé il y a %s." % (msg.cmd[0], msg.just_countdown(datetime.now () - STREND[msg.cmd[0]].start)))
  elif msg.cmd[0] in EVENTS:
    (day, msg_before, msg_after) = EVENTS[msg.cmd[0]]
    if day is None:
      msg.send_chn (msg_before)
    else:
      msg.send_chn (msg.countdown_format (day, msg_before, msg_after))
    return True
  else:
    return False


def parseask(msg):
  msgl = msg.content.lower ()
  if re.match("^.*((create|new) +(a|an|a +new|an *other)? *(events?|commande?)|(nouvel(le)?|ajoute|cr[ée]{1,3}) +(un)? *([eé]v[ée]nements?|commande?)).*$", msgl) is not None:
    name = re.match("^.*!([^ \"'@!]+).*$", msg.content)
    if name is not None and name.group (1) not in EVENTS:
      texts = re.match("^[^\"]*(avant|après|apres|before|after)?[^\"]*\"([^\"]+)\"[^\"]*((avant|après|apres|before|after)?.*\"([^\"]+)\".*)?$", msg.content)
      if texts is not None and texts.group (3) is not None:
        extDate = msg.extractDate ()
        if extDate is None or extDate == "":
          msg.send_snd ("La date de l'événement est invalide...")
        else:
          if texts.group (1) is not None and (texts.group (1) == "après" or texts.group (1) == "apres" or texts.group (1) == "after"):
            msg_after = texts.group (2)
            msg_before = texts.group (5)
          if (texts.group (4) is not None and (texts.group (4) == "après" or texts.group (4) == "apres" or texts.group (4) == "after")) or texts.group (1) is None:
            msg_before = texts.group (2)
            msg_after = texts.group (5)

          if msg_before.find ("%s") != -1 and msg_after.find ("%s") != -1:
            EVENTS[name.group (1)] = (extDate, msg_before, msg_after)
            save_module ()
            msg.send_snd ("Nouvel événement !%s ajouté avec succès."%name.group (1))
          else:
            msg.send_snd ("Pour que l'événement soit valide, ajouter %s à l'endroit où vous voulez que soit ajouté le compte à rebours.")
      elif texts is not None and texts.group (2) is not None:
        EVENTS[name.group (1)] = (None, texts.group (2), None)
        save_module ()
        msg.send_snd ("Nouvelle commande !%s ajoutée avec succès."%name.group (1))
      else:
        msg.send_snd ("Veuillez indiquez les messages d'attente et d'après événement entre guillemets.")
    elif name is None:
      msg.send_snd ("Veuillez attribuer une commande à l'événement.")
    else:
      msg.send_snd ("Un événement portant ce nom existe déjà.")
  return False

def parselisten (msg):
  return False
