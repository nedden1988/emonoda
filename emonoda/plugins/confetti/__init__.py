"""
    Emonoda -- A set of tools to organize and manage your torrents
    Copyright (C) 2015  Devaev Maxim <mdevaev@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import pkgutil
import textwrap
import enum

import mako.template

from .. import BasePlugin


# =====
class ST(enum.Enum):
    INVALID = "invalid"
    NOT_IN_CLIENT = "not_in_client"
    UNKNOWN = "unknown"
    PASSED = "passed"
    UPDATED = "updated"
    ERROR = "error"
    EXCEPTION = "exception"


# =====
def templated(name, **kwargs):
    data = pkgutil.get_data(__name__, os.path.join("templates", name))
    template = textwrap.dedent(data.decode()).strip()
    return mako.template.Template(template).render(**kwargs).strip()


# =====
class BaseConfetti(BasePlugin):
    def __init__(self, **_):
        pass

    def send_results(self, app, results):
        raise NotImplementedError