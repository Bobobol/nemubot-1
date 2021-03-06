# -*- coding: utf-8 -*-

# Nemubot is a smart and modulable IM bot.
# Copyright (C) 2012-2014  nemunaire
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

from message import TextMessage
from message.visitor import AbstractVisitor


class IRC(AbstractVisitor):

    def __init__(self):
        self.pp = ""


    def visit_TextMessage(self, msg):
        self.pp += "PRIVMSG %s :" % ",".join(msg.to)
        if isinstance(msg.message, str):
            self.pp += msg.message
        else:
            msg.message.accept(self)
        self.pp += "\r\n"


    def visit_DirectAsk(self, msg):
        others = [to for to in msg.to if to != msg.designated]

        # Avoid nick starting message when discussing on user channel
        if len(others) != len(msg.to):
            res = TextMessage(msg.message,
                              server=msg.server, date=msg.date,
                              to=msg.to, frm=msg.frm)
            res.accept(self)

        if len(others):
            res = TextMessage("%s: %s" % (msg.designated, msg.message),
                              server=msg.server, date=msg.date,
                              to=others, frm=msg.frm)
            res.accept(self)


    def visit_Command(self, msg):
        res = TextMessage("!%s%s%s" % (msg.cmd,
                                       " " if len(msg.args) else "",
                                       " ".join(msg.args)),
                          server=msg.server, date=msg.date,
                          to=msg.to, frm=msg.frm)
        res.accept(self)


    def visit_OwnerCommand(self, msg):
        res = TextMessage("`%s%s%s" % (msg.cmd,
                                       " " if len(msg.args) else "",
                                       " ".join(msg.args)),
                          server=msg.server, date=msg.date,
                          to=msg.to, frm=msg.frm)
        res.accept(self)
