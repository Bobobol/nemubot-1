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

import imp
import logging
import os
import xmlparser

logger = logging.getLogger("nemubot.prompt.builtins")

def end(toks, context, prompt):
    """Quit the prompt for reload or exit"""
    if toks[0] == "refresh":
        return "refresh"
    elif toks[0] == "reset":
        return "reset"
    else:
        context.quit()
    return "quit"


def liste(toks, context, prompt):
    """Show some lists"""
    if len(toks) > 1:
        for l in toks[1:]:
            l = l.lower()
            if l == "server" or l == "servers":
                for srv in context.servers.keys():
                    print ("  - %s ;" % srv)
                if len(context.servers) == 0:
                    print ("  > No server loaded")
            elif l == "mod" or l == "mods" or l == "module" or l == "modules":
                for mod in context.modules.keys():
                    print ("  - %s ;" % mod)
                if len(context.modules) == 0:
                    print ("  > No module loaded")
            elif l in prompt.HOOKS_LIST:
                (f,d) = prompt.HOOKS_LIST[l]
                f(d, context, prompt)
            else:
                print ("  Unknown list `%s'" % l)
    else:
        print ("  Please give a list to show: servers, ...")


def load_file(filename, context):
    if os.path.isfile(filename):
        config = xmlparser.parse_file(filename)

        # This is a true nemubot configuration file, load it!
        if (config.getName() == "botconfig"
            or config.getName() == "nemubotconfig"):
            # Preset each server in this file
            for server in config.getNodes("server"):
                ip = server["ip"] if server.hasAttribute("ip") else config["ip"]
                nick = server["nick"] if server.hasAttribute("nick") else config["nick"]
                owner = server["owner"] if server.hasAttribute("owner") else config["owner"]
                realname = server["realname"] if server.hasAttribute("realname") else config["realname"]
                if context.add_server(server, nick, owner, realname):
                    print("Server `%s:%s' successfully added." %
                          (server["host"], server["port"]))
                else:
                    print("Server `%s:%s' already added, skiped." %
                          (server["host"], server["port"]))

            # Load module and their configuration
            for mod in config.getNodes("module"):
                context.modules_configuration[mod["name"]] = mod
                if not mod.hasAttribute("autoload") or (mod["autoload"].lower() != "false" and mod["autoload"].lower() != "off"):
                    __import__(mod["name"])

            # Load files asked by the configuration file
            for load in config.getNodes("include"):
                load_file(load["path"], context)

        # Other formats
        else:
            print ("  Can't load `%s'; this is not a valid nemubot "
                   "configuration file." % filename)

    # Unexisting file, assume a name was passed, import the module!
    else:
        tt = __import__(filename)
        imp.reload(tt)


def load(toks, context, prompt):
    """Load an XML configuration file"""
    if len(toks) > 1:
        for filename in toks[1:]:
            load_file(filename, context)
    else:
        print ("Not enough arguments. `load' takes a filename.")
    return


def select(toks, context, prompt):
    """Select the current server"""
    if (len(toks) == 2 and toks[1] != "None"
        and toks[1] != "nemubot" and toks[1] != "none"):
        if toks[1] in context.servers:
            prompt.selectedServer = context.servers[toks[1]]
        else:
            print ("select: server `%s' not found." % toks[1])
    else:
        prompt.selectedServer = None
    return


def unload(toks, context, prompt):
    """Unload a module"""
    if len(toks) == 2 and toks[1] == "all":
        for name in context.modules.keys():
            context.unload_module(name)
    elif len(toks) > 1:
        for name in toks[1:]:
            if context.unload_module(name):
                print ("  Module `%s' successfully unloaded." % name)
            else:
                print ("  No module `%s' loaded, can't unload!" % name)
    else:
        print ("Not enough arguments. `unload' takes a module name.")


def debug(toks, context, prompt):
    """Enable/Disable debug mode on a module"""
    if len(toks) > 1:
        for name in toks[1:]:
            if name in context.modules:
                context.modules[name].DEBUG = not context.modules[name].DEBUG
                if context.modules[name].DEBUG:
                    print ("  Module `%s' now in DEBUG mode." % name)
                else:
                    print ("  Debug for module module `%s' disabled." % name)
            else:
                print ("  No module `%s' loaded, can't debug!" % name)
    else:
        print ("Not enough arguments. `debug' takes a module name.")


#Register build-ins
CAPS = {
  'quit': end, #Disconnect all server and quit
  'exit': end, #Alias for quit
  'reset': end, #Reload the prompt
  'refresh': end, #Reload the prompt but save modules
  'load': load, #Load a servers or module configuration file
  'unload': unload, #Unload a module and remove it from the list
  'select': select, #Select a server
  'list': liste, #Show lists
  'debug': debug, #Pass a module in debug mode
}
