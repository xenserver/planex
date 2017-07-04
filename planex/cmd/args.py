"""
Common argparse utilities for planex command line tools
"""

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
