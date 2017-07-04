"""
Common argparse utilities for planex command line tools
"""

import argparse
import pkg_resources


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


def rpm_macro(string):
    """
    Argparse type handler for RPM macro command line arguments of the form:

       --define "foo bar"

    Returns a (foo, bar) tuple if successful, otherwise raises
    ArgumentTypeError.
    """
    macro = tuple(string.split(' ', 1))

    if len(macro) != 2:
        msg = "malformed macro passed to --define: %r" % string
        raise argparse.ArgumentTypeError(msg)

    return macro
