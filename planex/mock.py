"""
planex-build-mock: Wrapper around mock
"""

import subprocess
import sys
from uuid import uuid4

import argparse
import argcomplete
from planex.util import add_common_parser_options


def parse_args_or_exit(argv):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Planex build system in a chroot (a mock wrapper)')
    add_common_parser_options(parser)
    parser.add_argument(
        "--configdir", metavar="CONFIGDIR", default=None,
        help="Change where the config files are found")
    parser.add_argument(
        "--resultdir", metavar="RESULTDIR", default=None,
        help="Path for resulting files to be put")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' \
              define MACRO with value EXPR for the build")
    parser.add_argument('srpms', metavar='SRPM', nargs='+',
                        help='SRPM to build in the chroot')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def get_command_line(args, defaults):
    """
    Return mock command line and arguments
    """
    cmd = ['mock']
    if args.quiet:
        cmd.append('--quiet')
    for define in args.define:
        cmd.append('--define')
        cmd.append(define)
    if args.configdir is not None:
        cmd.append('--configdir')
        cmd.append(args.configdir)
    if args.resultdir is not None:
        cmd.append("--resultdir")
        cmd.append(args.resultdir)
    cmd.extend(defaults)
    cmd.extend(args.srpms)
    return cmd


def main(argv=None):
    """
    Entry point arguments: srpm0 srpm1 srpm2 ...
    At least one SRPM file (with ".src.rpm" or ".srpm" extension)
    should be present.
    """

    defaults = [
        "--uniqueext", uuid4().hex,
        "--disable-plugin", "package_state",
        "--rebuild"
    ]

    args = parse_args_or_exit(argv)

    cmd = get_command_line(args, defaults)
    return_value = subprocess.call(cmd)
    sys.exit(return_value)
