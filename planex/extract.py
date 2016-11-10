"""
planex-extract: Extract files from a tarball as described by a link file
"""

import argparse
import json
import logging
import os
import os.path
import sys
import tarfile

import argcomplete

from planex.util import add_common_parser_options
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


def copy_spec(spec_in, spec_out):
    """
    Copy contents of file named by spec_in to the file handle spec_out
    """
    with open(spec_in) as fh_in:
        for line in fh_in:
            spec_out.write(line)


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
    parser.add_argument("-t", "--topdir", metavar="DIR", default=None,
                        help="Set rpmbuild toplevel directory [deprecated]")
    parser.add_argument("-D", "--define", default=[], action="append",
                        help="--define='MACRO EXPR' define MACRO with "
                        "value EXPR")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function.  Fetch sources directly or via a link file.
    """

    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    try:
        with open(args.link) as fileh:
            link = json.load(fileh)

    except IOError as exn:
        # IO error loading JSON file
        sys.exit("%s: %s: %s" %
                 (sys.argv[0], exn.strerror, exn.filename))

    # Extract the spec file
    with tarfile.open(args.tarball) as tar:
        tar_root = archive_root(tar)
        extract_file(tar, os.path.join(tar_root, str(link['specfile'])),
                     args.output + '.tmp')

        macros = [tuple(macro.split(' ', 1)) for macro in args.define]

        if any(len(macro) != 2 for macro in macros):
            _err = [macro for macro in macros if len(macro) != 2]
            print "error: malformed macro passed to --define: %r" % _err
            sys.exit(1)

        # When using deprecated arguments, we want them at the top of the
        # macros list
        if args.topdir is not None:
            print "# warning: --topdir is deprecated"
            macros.insert(0, ('_topdir', args.topdir))

        with open(args.output, "w") as spec_fh:
            if 'branch' in link:
                spec_fh.write("%%define branch %s\n" % link['branch'])
            copy_spec(args.output + '.tmp', spec_fh)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
