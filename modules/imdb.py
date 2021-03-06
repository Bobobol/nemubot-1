# coding=utf-8

"""Show many information about a movie or serie"""

import json
import re
import urllib.request

from hooks import hook

nemubotversion = 3.4

from more import Response

def help_full():
    return "Search a movie title with: !imdbs <approximative title> ; View movie details with !imdb <title>"

def get_movie(title=None, year=None, imdbid=None, fullplot=True, tomatoes=False):
    """Returns the information about the matching movie"""

    # Built URL
    url = "http://www.omdbapi.com/?"
    if title is not None:
        url += "t=%s&" % urllib.parse.quote(title)
    if year is not None:
        url += "y=%s&" % urllib.parse.quote(year)
    if imdbid is not None:
        url += "i=%s&" % urllib.parse.quote(imdbid)
    if fullplot:
        url += "plot=full&"
    if tomatoes:
        url += "tomatoes=true&"

    print_debug(url)

    # Make the request
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode())

    # Return data
    if "Error" in data:
        raise IRCException(data["Error"])

    elif "Response" in data and data["Response"] == "True":
        return data

    else:
        raise IRCException("An error occurs during movie search")

def find_movies(title):
    """Find existing movies matching a approximate title"""

    # Built URL
    url = "http://www.omdbapi.com/?s=%s" % urllib.parse.quote(title)
    print_debug(url)

    # Make the request
    raw = urllib.request.urlopen(url)
    data = json.loads(raw.read().decode())

    # Return data
    if "Error" in data:
        raise IRCException(data["Error"])

    elif "Search" in data:
        return data

    else:
        raise IRCException("An error occurs during movie search")


@hook("cmd_hook", "imdb")
def cmd_imdb(msg):
    """View movie details with !imdb <title>"""
    if len(msg.cmds) < 2:
        raise IRCException("precise a movie/serie title!")

    title = ' '.join(msg.cmds[1:])

    if re.match("^tt[0-9]{7}$", title) is not None:
        data = get_movie(imdbid=title)
    else:
        rm = re.match(r"^(.+)\s\(([0-9]{4})\)$", title)
        if rm is not None:
            data = get_movie(title=rm.group(1), year=rm.group(2))
        else:
            data = get_movie(title=title)

    res =  Response(channel=msg.channel,
                    title="%s (%s)" % (data['Title'], data['Year']),
                    nomore="No more information, more at http://www.imdb.com/title/%s" % data['imdbID'])

    res.append_message("\x02rating\x0F: %s (%s votes); \x02plot\x0F: %s" %
                       (data['imdbRating'], data['imdbVotes'], data['Plot']))

    res.append_message("%s \x02from\x0F %s \x02released on\x0F %s; \x02genre:\x0F %s; \x02directed by:\x0F %s; \x02writed by:\x0F %s; \x02main actors:\x0F %s"
                       % (data['Type'], data['Country'], data['Released'], data['Genre'], data['Director'], data['Writer'], data['Actors']))
    return res

@hook("cmd_hook", "imdbs")
def cmd_search(msg):
    """!imdbs <approximative title> to search a movie title"""

    data = find_movies(' '.join(msg.cmds[1:]))

    movies = list()
    for m in data['Search']:
        movies.append("\x02%s\x0F (%s of %s)" % (m['Title'], m['Type'], m['Year']))

    return Response(movies, title="Titles found", channel=msg.channel)
