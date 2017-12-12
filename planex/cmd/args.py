"""
Common argparse utilities for planex command line tools
"""

import argparse
import pkg_resources


def common_base_parser():
    """
    Returns a parser which handles the following common flags:
        * --quiet/--warn
        * -v/--verbose/--debug
        * --version

    This parser can then be used as a 'parent' to other parsers
    which will inherit these options.

    See https://docs.python.org/2.7/library/argparse.html#parents
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--quiet', '--warn', action='store_true',
                        help='Only log warnings and errors')
    parser.add_argument('-v', '--verbose', '--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--version', action='version', version="%%(prog)s %s" %
                        pkg_resources.require("planex")[0].version)
    return parser


def rpm_define_parser():
    """
    Returns a parser which handles rpmbuild-style "--define 'name macro'"
    options.

    This parser can then be used as a 'parent' to other parsers
    which will inherit these options.

    See https://docs.python.org/2.7/library/argparse.html#parents
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-D", "--define", default=[], action="append",
                        type=rpm_macro,
                        help="--define='MACRO EXPR' "
                             "define MACRO with value EXPR")
    return parser


def keeptmp_parser():
    """
    Returns a parser which handles the "--keeptmp" option.

    This parser can then be used as a 'parent' to other parsers
    which will inherit these options.

    See https://docs.python.org/2.7/library/argparse.html#parents
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--keeptmp", action="store_true",
                        help="Keep temporary files")
    return parser


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
