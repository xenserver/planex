#!/usr/bin/env python

# Some generic utils used by several other files

import subprocess
import os
import pipes
import urlparse
import sys
import tempfile
import yum

dump_cmds = True

class bcolours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def print_col(col, msg):
    if sys.stdout.isatty():
        print col, msg, bcolours.ENDC
    else:
        print msg
    sys.stdout.flush()


def rewrite_url(url, destination=None):
    """
    Rewrite url to point to destination
    """
    (scheme, host, path, _, _, fragment) = urlparse.urlparse(url)
    if destination=="" or scheme in ["git", "hg"]:
        return url

    else:
        basename = path.split("/")[-1]
        return destination + basename + fragment


def load_mock_config(cfg):
    """
    Load the yum configuration from the mock configuration file
    Nasty, but this is how mock loads its configuration file...
    From /usr/sbin/mock
    """

    import mockbuild.util
    unprivUid = os.getuid()
    __VERSION__ = 1
    PKGPYTHONDIR = mockbuild.__path__[0]
    config_opts = mockbuild.util.setup_default_config_opts(unprivUid,
        __VERSION__, PKGPYTHONDIR)
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


def run(cmd, check=True, env=None, inputtext=None):
    """
    Run a command, dumping it cut-n-pasteably if required. Checks the return
    code unless check=False. Returns a dictionary of stdout, stderr and return
    code (rc)
    """
    if dump_cmds:
        print_col(bcolours.WARNING, "CMD: " + (" ".join(map(pipes.quote,cmd))))

    if env == None:
        env = os.environ.copy()

    proc = subprocess.Popen(cmd, env=env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    [stdout,stderr] = proc.communicate(inputtext)

    if check and proc.returncode != 0:
        print_col(bcolours.FAIL, "ERROR: command failed")
        print "Command was:\n\n  %s\n" % (" ".join(map(pipes.quote,cmd)))
        print "stdout"
        print "------"
        print stdout
        print "stderr"
        print "------"
        print stderr
        raise Exception
            
    return {"stdout":stdout, "stderr":stderr, "rc":proc.returncode}
