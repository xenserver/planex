"""
planex-extract: Extract files from a tarball as described by a link file
"""

import argparse
import logging
import os
import os.path
import sys
import tarfile

import argcomplete

from planex.link import Link
from planex.cmd.args import add_common_parser_options
from planex.util import setup_logging
from planex.util import setup_sigint_handler


def extract_file(tar, name_in, name_out):
    """
    Extract a file from a tarball
    """
    logging.debug("Extracting %s to %s", name_in, name_out)
    if name_in not in tar.getnames():
        sys.exit("%s: %s not found in archive" % (sys.argv[0], name_in))
    mem = tar.getmember(name_in)
    mem.name = os.path.basename(name_out)
    tar.extract(mem, os.path.dirname(name_out))
    os.utime(name_out, None)


def archive_root(tar):
    """
    Return the name of the top level directory of the tarball
    """
    names = tar.getnames()
    topname = os.path.commonprefix(names)
    if topname in names:
        top_element = tar.getmember(topname)
        if top_element.isdir():
            return topname
    return ''


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="Extract package sources")
    add_common_parser_options(parser)
    parser.add_argument("tarball", help="Tarball")
    parser.add_argument("-l", "--link", help="Link file")
    parser.add_argument("-o", "--output", metavar="SPEC",
                        help="Output spec file")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Main function.  Fetch sources directly or via a link file.
    """

    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    link = Link(args.link)

    # Extract the spec file
    with tarfile.open(args.tarball) as tar:
        tar_root = archive_root(tar)
        extract_file(tar, os.path.join(tar_root, link.specfile), args.output)
