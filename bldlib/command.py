"""
Command-related functions.
"""

import io
import shlex
import subprocess
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
    logger.debug("Running %s", command)

    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
            logger.error("An error occurred when executing %s:\n" +
                         "==========\n" +
                         "%s\n" +
                         "==========", command, buffer.getvalue())
            raise CommandException(
                "An error occurred when executing %s" % command)
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
        for line in self._fd.readlines():
            decoded_line = line.decode('utf-8')
            self._logger.info(decoded_line.strip())
            self._buffer.write(decoded_line)
