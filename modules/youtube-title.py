import urllib.request
from bs4 import BeautifulSoup
from hooks import hook
from more import Response

nemubotversion = 3.4

def help_tiny():
  return "CVE description"

def help_full():
  return "No help "

@hook("cmd_hook", "yt")
def get_info_yt(msg):
  req = urllib.request.Request('https://www.youtube.com/watch?v=e0MCuuePNQg',
                               data=None,
                               headers={
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
      })

  url = urllib.request.urlopen(req)
  soup = BeautifulSoup(url)
  desc = soup.body.find(id='eow-title')
  res = Response(channel=msg.channel, nomore="No more description")
  res.append_message(desc.text)
  return res

