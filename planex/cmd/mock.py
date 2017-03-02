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
    parser.add_argument(
        "--init", action="store_true",
        help="initialize the chroot, do not build anything")
    parser.add_argument(
        "--rebuild", metavar="SRPM", nargs="+", dest="srpms",
        help='rebuild the specified SRPM(s)')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def mock(args, tmp_config_dir, *extra_params):
    """
    Return mock command line and arguments
    """

    print "Mock args ar %s" % args

    cmd = []
    cmd += ['stdbuf', '-o', 'L']
    cmd += ['mock']
    cmd += ["--uniqueext", uuid4().hex]
    cmd += ['--configdir', tmp_config_dir]

    if args.quiet:
        cmd += ['--quiet']
    if args.root is not None:
        cmd += ['--root', args.root]
    if args.resultdir is not None:
        cmd += ["--resultdir", args.resultdir]

    for define in args.define:
        cmd += ['--define', define]

    cmd.extend(extra_params)
    subprocess.check_call(cmd)


def createrepo(pkg_dir, metadata_dir, quiet=False):
    """
    Run createrepo.   Repository metadata will be created in
    metadata_dir/repodata.
    """
    cmd = ['createrepo']
    cmd += ['--baseurl=file://%s' % pkg_dir]
    cmd += ['--outputdir=%s' % metadata_dir]
    cmd += [pkg_dir]
    if quiet:
        cmd += ['--quiet']
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


def clone_mock_config(configdir, tmpdir):
    """
    Copy mock configuration files into a temporary directory,
    retaining modification times to prevent the mock chroot
    cache from being rebuilt.
    Returns the path to the temporary configuration.
    """
    clonedir = os.path.join(tmpdir, "mock")
    shutil.copytree(configdir, clonedir)
    return clonedir


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    tmpdir = tempfile.mkdtemp(prefix="px-mock-")
    config = clone_mock_config(args.configdir, tmpdir)

    try:
        if args.init:
            mock(args, config, "--init")

        else:
            config_in_path = os.path.join(args.configdir, args.root + ".cfg")
            config_out_path = os.path.join(config, args.root + ".cfg")
            insert_loopback_repo(config_in_path, config_out_path, tmpdir)
            createrepo(os.path.join(os.getcwd(), "RPMS"), tmpdir, args.quiet)
            mock(args, config, "--rebuild", *args.srpms)

    except subprocess.CalledProcessError as cpe:
        sys.exit(cpe.returncode)

    finally:
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
