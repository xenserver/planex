"""
planex-build-mock: Wrapper around mock
"""

import os
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

import argparse
import argcomplete
from planex.util import add_common_parser_options


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Planex build system in a chroot (a mock wrapper)')
    add_common_parser_options(parser)
    parser.add_argument(
        "--configdir", metavar="CONFIGDIR", default="/etc/mock",
        help="Change where the config files are found")
    parser.add_argument(
        "--root", "-r", metavar="CONFIG", default="default",
        help="Change where the config files are found")
    parser.add_argument(
        "--resultdir", metavar="RESULTDIR", default=None,
        help="Path for resulting files to be put")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="Keep temporary files")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' \
              define MACRO with value EXPR for the build")
    parser.add_argument('srpms', metavar='SRPM', nargs='+',
                        help='SRPM to build in the chroot')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def mock(args, tmp_config_dir, defaults):
    """
    Return mock command line and arguments
    """
    cmd = ['mock']
    if args.quiet:
        cmd.append('--quiet')
    for define in args.define:
        cmd.append('--define')
        cmd.append(define)
    cmd.append('--configdir')
    cmd.append(tmp_config_dir)
    if args.root is not None:
        cmd.append('--root')
        cmd.append(args.root)
    if args.resultdir is not None:
        cmd.append("--resultdir")
        cmd.append(args.resultdir)
    cmd.extend(defaults)
    cmd.extend(args.srpms)
    subprocess.check_call(cmd)


def createrepo(pkg_dir, metadata_dir, quiet=False):
    """
    Run createrepo
    """
    cmd = ['createrepo']
    cmd += ['--baseurl=file://%s' % pkg_dir]
    cmd += ['--outputdir=%s' % metadata_dir]
    cmd += [pkg_dir]
    if quiet:
        cmd.append('--quiet')
    subprocess.check_call(cmd)


def insert_loopback_repo(config_in_path, config_out_path, repo_path):
    """
    Write a new mock config, including a loopback repository configuration
    pointing to repo_path.    Ensure that the new config file's last-modified
    time is the same as the input file's, so that the mock chroot is not
    rebuilt.
    """
    with open(config_in_path) as config_in:
        with open(config_out_path, "w") as config_out:
            for line in config_in:
                config_out.write(line)
                if "config_opts['yum.conf']" in line:
                    config_out.write("[mock-loopback-%d]\n" % os.getpid())
                    config_out.write("name=Mock output\n")
                    config_out.write("baseurl = file://%s\n" % repo_path)
                    config_out.write("gpgcheck=0\n")
                    config_out.write("priority=1\n")
                    config_out.write("enabled=1\n")
                    config_out.write("metadata_expire=0\n")
                    config_out.write("\n")
    shutil.copystat(config_in_path, config_out_path)


def main(argv=None):
    """
    Entry point
    """

    defaults = [
        "--uniqueext", uuid4().hex,
        "--rebuild"
    ]

    args = parse_args_or_exit(argv)

    tmpdir = tempfile.mkdtemp(prefix="px-mock-")
    try:
        config_in = os.path.join(args.configdir, args.root + ".cfg")
        config_out = os.path.join(tmpdir, args.root + ".cfg")

        createrepo(os.path.join(os.getcwd(), "RPMS"), tmpdir, args.quiet)

        insert_loopback_repo(config_in, config_out, tmpdir)
        shutil.copy2(os.path.join(args.configdir, "logging.ini"),
                     os.path.join(tmpdir, "logging.ini"))
        shutil.copy2(os.path.join(args.configdir, "site-defaults.cfg"),
                     os.path.join(tmpdir, "site-defaults.cfg"))

        mock(args, tmpdir, defaults)

    except subprocess.CalledProcessError as cpe:
        sys.exit(cpe.returncode)

    finally:
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
