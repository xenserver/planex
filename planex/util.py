#!/usr/bin/env python

"""
Library of generic functions used by other planex components
"""

import subprocess
import sys
import os
import __main__
import pipes
import tempfile
import yum
import logging
import signal
import pkg_resources


def load_mock_config(cfg):
    """
    Load the yum configuration from the mock configuration file
    Nasty, but this is how mock loads its configuration file...
    From /usr/sbin/mock
    """

    import mockbuild.util  # pylint: disable=F0401
    unpriv_uid = os.getuid()
    version = 1
    pkgpythondir = mockbuild.__path__[0]
    config_opts = mockbuild.util.setup_default_config_opts(
        unpriv_uid, version, pkgpythondir)
    config_opts['config_paths'] = []
    config_opts['config_paths'].append(cfg)
    execfile(cfg)
    return config_opts


def get_yumbase(config):
    """
    Initialise the Yum library and return an object which can be
    used to query the package database
    """
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(config['yum.conf'])
        temp.flush()

        yumbase = yum.YumBase()
        yumbase.repos.disableRepo('*')
        yumbase.getReposFromConfigFile(temp.name)

    return yumbase


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


def add_common_parser_options(parser):
    """
    Takes a parser and adds the following command line flags:
        * --quiet/--warn
        * -v/--verbose/--debug
        * --version
    """
    parser.add_argument('--quiet', '--warn', action='store_true',
                        help='Only log warnings and errors')
    parser.add_argument('-v', '--verbose', '--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--version', action='version', version="%%(prog)s %s" %
                        pkg_resources.require("planex")[0].version)
