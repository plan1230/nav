#
# Copyright (C) 2008-2012 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""Logging utilities for ipdevpoll"""

import logging
from logging import Formatter
import inspect

from nav.loggeradapter import LoggerAdapter


def get_context_logger(instance, **kwargs):
    """Returns a LoggerAdapter with the given context."""
    if isinstance(instance, basestring):
        logger = logging.getLogger(instance)
    else:
        logger = get_class_logger(instance.__class__)

    return LoggerAdapter(logger, extra=kwargs)

def get_class_logger(cls):
    """Return a logger instance for a given class object.

    The logger object is named after the fully qualified class name of
    the cls class.

    """
    full_class_name = "%s.%s" % (cls.__module__, cls.__name__)
    return logging.getLogger(full_class_name.lower())

class ContextFormatter(Formatter):
    """A log formatter that will add context data if available in the record.

    Only recognizes the attributes 'job' and 'sysname' as context data.

    """
    prefix = 'nav.ipdevpoll.'

    def __init__(self):
        self._normal_fmt = "%(asctime)s [%(levelname)s %(name)s] %(message)s"
        self._context_fmt = ("%(asctime)s [%(levelname)s "
                             "%(name)s] [%(context)s] %(message)s")
        Formatter.__init__(self, self._normal_fmt)

    def format(self, record):
        """Overridden to choose format based on record contents."""
        self._set_context(record)
        self._strip_logger_prefix(record)
        return Formatter.format(self, record)

    def _set_context(self, record):
        context = [getattr(record, attr)
                   for attr in ('job', 'sysname')
                   if hasattr(record, attr)]
        if context:
            record.__dict__['context'] = ' '.join(context)
            self._fmt = self._context_fmt
        else:
            self._fmt = self._normal_fmt

    def _strip_logger_prefix(self, record):
        if record.name.startswith(self.prefix):
            record.name = record.name[len(self.prefix):]

# pylint: disable=R0903
class ContextLogger(object):
    """Descriptor for getting an appropriate logger instance.

    A class that needs logging can use this descriptor to automatically get a
    logger with the correct name and context.  Example::

      class Foo(object):
          _logger = ContextLogger()

          def do_bar(self):
              self._logger.debug("now doing bar")

    The _logger attribute will be either a logging.Logger or
    logging.LoggerAdapter, depending on whether a logging context can be
    found.  The first time _logger is accessed, it establishes the context
    either via direct lookup on the owning instance, or via stack frame
    inspection.  If the current instance hasn't already established a logging
    context, but the calling client object has one, this context will be
    copied permanently to this instance.

    """
    log_attr = '_logger_object'

    def __init__(self, suffix=None, context_vars=None):
        self.suffix = suffix
        self.context_vars = context_vars

    def __get__(self, obj, owner=None):
        target = owner if obj is None else obj
        if hasattr(target, self.log_attr):
            return getattr(target, self.log_attr)

        logger = logging.getLogger(self._logger_name(owner))
        if target is obj:
            if self.context_vars:
                extra = dict((k, getattr(target, k, None))
                              for k in self.context_vars)
            elif hasattr(target, '_log_context'):
                extra = getattr(target, '_log_context')
            else:
                extra = self._context_search(inspect.stack())

            if extra:
                logger = LoggerAdapter(logger, extra)

        setattr(target, self.log_attr, logger)
        return logger

    def _logger_name(self, klass):
        if klass.__module__ != '__main__':
            name = "%s.%s" % (klass.__module__, klass.__name__)
        else:
            name = klass.__name__.lower()
        if self.suffix:
            name = name + '.' + self.suffix
        return name.lower()

    @staticmethod
    def _context_search(stack, maxdepth=10):
        """Attempts to extract a logging context from the current stack"""
        def inspect_frame(frame):
            obj = frame.f_locals.get('self', None)
            if obj is None:
                return
            if hasattr(obj, '_log_context'):
                return getattr(obj, '_log_context')
            elif hasattr(obj, '_logger'):
                logger = getattr(obj, '_logger')
                if hasattr(logger, 'extra'):
                    return logger.extra

        frames = (s[0] for s in stack[1:maxdepth])
        for frame in frames:
            extra = inspect_frame(frame)
            if extra:
                return extra
        return None

    def __set__(self, obj, value):
        raise AttributeError(
            "cannot reassign a %s attribute" % self.__class__.__name__)

    def __delete__(self, obj):
        raise AttributeError(
            "cannot delete a %s attribute" % self.__class__.__name__)
