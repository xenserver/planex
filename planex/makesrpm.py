#!/usr/bin/python

"""
planex-make-srpm: Wrapper around rpmbuild
"""

import sys
import subprocess
import os
from shutil import copyfile, rmtree
import fileinput
import tarfile
import tempfile

import argparse
import argcomplete
from planex.util import add_common_parser_options


def parse_args_or_exit(argv):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Planex SRPM building')
    add_common_parser_options(parser)
    parser.add_argument("spec", metavar="SPEC", help="Spec file")
    parser.add_argument("sources", metavar="SOURCES", nargs='*',
                        help="Source files")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    parser.add_argument(
        "--topdir", metavar="DIR", default=None,
        help='Set rpmbuild toplevel directory [deprecated]')
    parser.add_argument(
        "--dist", metavar="DIST", default=None,
        help="distribution tag (used in RPM filenames) [deprecated]")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="keep temporary files")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def setup_tmp_area():
    """
    Create temporary working area
    """
    tmp_dirpath = tempfile.mkdtemp()
    tmp_specs = os.path.join(tmp_dirpath, 'SPECS')
    tmp_sources = os.path.join(tmp_dirpath, 'SOURCES')

    os.makedirs(tmp_specs)
    os.makedirs(tmp_sources)

    return (tmp_dirpath, tmp_specs, tmp_sources)


def extract_topdir(tmp_specfile, source):
    """
    Set the topdir name taken from the source tarball
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if 'autosetup' in line:
            tar = tarfile.open(source)
            names = tar.getnames()
            topname = os.path.commonprefix(names)
            if topname in names:
                top_element = tar.getmember(topname)
                if top_element.isdir():
                    print "%s -n %s" % (line.strip(), topname)
            else:
                print "%s -c" % line.strip()
        else:
            print line,


def get_command_line(args, tmp_sources, tmp_specfile):
    """
    Return rpmbuild command line and arguments
    """
    cmd = ['rpmbuild']
    if args.quiet:
        cmd.append('--quiet')
    if args.topdir is not None:
        cmd.append('--define')
        cmd.append('_topdir %s' % args.topdir)
    if args.dist is not None:
        cmd.append('--define')
        cmd.append('%%dist %s' % args.dist)
    for define in args.define:
        cmd.append('--define')
        cmd.append(define)
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmp_sources)
    cmd.append('-bs')
    cmd.append(tmp_specfile)

    return cmd


def main(argv):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)
    tmp_dirpath, tmp_specs, tmp_sources = setup_tmp_area()
    tmp_specfile = os.path.join(tmp_specs, os.path.basename(args.spec))

    try:
        # Copy files to temporary working area
        copyfile(args.spec, tmp_specfile)
        tarball_filters = ['.tar.gz', '.tar.bz2']

        for source in args.sources:
            if any([ext in source for ext in tarball_filters]):
                extract_topdir(tmp_specfile, source)
            dest = os.path.join(tmp_sources, os.path.basename(source))
            copyfile(source, dest)

        cmd = get_command_line(args, tmp_sources, tmp_specfile)
        return_value = subprocess.call(cmd)
        sys.exit(return_value)

    except IOError as exc:
        print "Copyfile: destination location must be writable"
        print "Exception: %s" % exc
    except (tarfile.TarError, tarfile.ReadError) as exc:
        print "Error when extracting patchqueue from tarfile"
        print "Exception: %s" % exc

    finally:
        # Clean temporary area (unless debugging)
        if args.keeptmp:
            print "Working directory retained at %s" % tmp_dirpath
        else:
            rmtree(tmp_dirpath)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
