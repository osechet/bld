"""
Logging functions.
"""

from datetime import datetime
import logging

from colors import color


class ColoredFormatter(logging.Formatter):
    """
    A logging formatter using ansi code to format the message.
    """

    COLORS = {
        'WARNING': 'yellow',
        'INFO': None,
        'DEBUG': 'cyan',
        'CRITICAL': 'red',
        'ERROR': 'red'
    }

    def format(self, record):
        level_name = record.levelname
        level_color = None
        if level_name in ColoredFormatter.COLORS:
            level_color = ColoredFormatter.COLORS[level_name]
        time = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        colored_time = color(time, style='bold')
        if record.args:
            colored_msg = color(record.msg % record.args, fg=level_color)
        else:
            colored_msg = color(record.msg, fg=level_color)
        return '%s - %s' % (colored_time, colored_msg)


class Logger:
    """
    A logger wrapper. This class is used to control verbosity.
    """

    def __init__(self):
        self._logger = logging.getLogger('bld')
        self._verbose = False

    @property
    def verbose(self):
        """
        Returns the verbose flag.
        """
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        """
        Sets the verbose flag.
        """
        self._verbose = value

    def error(self, message, *args, **kwargs):
        """
        Error log the given message.
        """
        self._logger.error(message + '\x1b[K', *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """
        Warning log the given message.
        """
        self._logger.warning(message + '\x1b[K', *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """
        Info log the given message.
        """
        if self._verbose:
            self._logger.info(message + '\x1b[K', *args, **kwargs)

    def log(self, message, *args, **kwargs):
        """
        Log the given message ignoring the verbosity.
        """
        self._logger.info(message + '\x1b[K', *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        """
        Debug log the given message.
        """
        # Debug messages are not subject to verbosity. If debug is on,
        # they are always displayed.
        self._logger.debug(message + '\x1b[K', *args, **kwargs)
