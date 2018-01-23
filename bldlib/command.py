"""
Command-related functions.
"""

import io
import platform
import shlex
import subprocess
import sys
import threading


class CommandException(Exception):
    """
    Command-related exception.
    """
    pass


def run(command, logger):
    """
    Run the given command. It can be provided as a list of arguments or as a string.abs
    If command is a string, it is splitted using shlex.split to preserve quoted groups.
    """
    if not isinstance(command, list):
        command = shlex.split(command)
    logger.debug("Running %s", shlex.quote(' '.join(command)))

    process = subprocess.Popen(command, shell=(platform.system() == 'Windows'),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        buffer = io.StringIO()
        stdout_reader = AsynchronousFileReader(process.stdout, buffer, logger)
        stdout_reader.start()
        stderr_reader = AsynchronousFileReader(process.stderr, buffer, logger)
        stderr_reader.start()

        process.wait()

        stdout_reader.join()
        stderr_reader.join()

        # Close subprocess' file descriptors.
        process.stdout.close()
        process.stderr.close()

        if process.returncode != 0:
            raise CommandException("""An error occurred when executing %s:
==========
%s
==========""" % (command, buffer.getvalue()))
    finally:
        buffer.close()


class AsynchronousFileReader(threading.Thread):
    """
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    """

    def __init__(self, fd, buffer, logger):
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self._fd = fd
        self._buffer = buffer
        self._logger = logger

    def run(self):
        """
        The body of the thread: read lines and write them in the buffer.
        """
        width = self._tty_width() if not self._logger.verbose else 0
        for line in iter(self._fd):
            decoded_line = line.decode('utf-8')
            strip_text = decoded_line.rstrip()
            self._logger.info(strip_text)
            self._buffer.write(decoded_line)
            if not self._logger.verbose:
                # Temporary print the output (help to see the command is running)
                sys.stdout.write('%s\x1b[K\r' % strip_text.expandtabs()[:width-5])
                sys.stdout.flush()

    def _tty_width(self):
        columns = 30
        if platform.system() == 'Windows':
            try:
                result = subprocess.check_output(['mode.com', 'con'])
                for line in result.decode('utf-8').splitlines():
                    if 'Columns:' in line:
                        columns = int(line.split(':')[1].strip())
            except subprocess.CalledProcessError:
                pass
        else:
            try:
                _, columns = subprocess.check_output(['stty', 'size']).split()
                columns = int(columns)
            except subprocess.CalledProcessError:
                pass
        return columns
