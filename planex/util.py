"""
Library of generic functions used by other planex components
"""

import errno
import json
import logging
import os
import pipes
import signal
import subprocess
import sys

from planex.config import Configuration

import __main__


def run(cmd, check=True, env=None, inputtext=None, logfiles=None):
    """
    Run a command, dumping it cut-n-pasteably if required. Checks the return
    code unless check=False. Returns a dictionary of stdout, stderr and return
    code (rc)
    """
    if logfiles is None:
        logfiles = []

    logging.debug("running command: %s",
                  (" ".join([pipes.quote(word) for word in cmd])))

    if env is None:
        env = os.environ.copy()

    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    [stdout, stderr] = proc.communicate(inputtext)

    if check and proc.returncode != 0:
        logging.error("command failed: %s",
                      (" ".join([pipes.quote(word) for word in cmd])))
        logging.error("stdout: %s", stdout)
        logging.error("stderr: %s", stderr)
        for log_path in logfiles:
            with open(log_path) as log_file:
                logging.error("%s:\n%s", log_path, log_file.read())
        raise Exception

    return {"stdout": stdout, "stderr": stderr, "rc": proc.returncode}


def add_custom_headers_for_url(netloc, headers):
    """
    Looks up custom headers from rc files and adds to the supplied headers
    """
    custom_headers = Configuration.get(netloc, 'Headers')
    if custom_headers:
        header_parts = json.loads(custom_headers)
        for key in header_parts.keys():
            headers.update({key: header_parts[key]})


def setup_sigint_handler():
    """
    Exit with 130 upon CTRL-C (http://tldp.org/LDP/abs/html/exitcodes.html
    """
    signal.signal(signal.SIGINT, lambda _: sys.exit(130))


def setup_logging(args):
    """
    Intended to be called by any top-level module to set up "sensible" logging.
    """
    # use lowercase (and abbreviated to max 5 chars) level names
    logging.addLevelName(logging.DEBUG, "debug")
    logging.addLevelName(logging.INFO, "info")
    logging.addLevelName(logging.WARNING, "warn")
    logging.addLevelName(logging.ERROR, "error")
    logging.addLevelName(logging.CRITICAL, "crit")

    tag = os.path.basename(__main__.__file__)

    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    if args.quiet:
        loglevel = logging.WARN

    datefmt = '%b %d %H:%M:%S'
    fmt = ('%(asctime)s.%(msecs).3d ' + tag +
           ' [%(process)d] %(levelname)5s: %(message)s')

    logging.basicConfig(format=fmt, datefmt=datefmt, level=loglevel)
    logging.debug("Initialised logging.")


def makedirs(path):
    """
    Recursively create path.  Do not raise an error if path already exists.
    """
    if not path:
        return
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def dedupe(items, key):
    """
    Return items with all but the first of each item matching key removed
    Order of items is preserved.
    """
    seen = set()
    ret = []
    for item in items:
        _key = key(item)
        if _key not in seen:
            seen.add(_key)
            ret.append(item)
    return ret
