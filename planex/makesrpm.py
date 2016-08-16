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
    parser.add_argument(
        "--topdir", metavar="DIR", default=None,
        help='Set rpmbuild toplevel directory')
    parser.add_argument(
        "--dist", metavar="DIST", default=None,
        help="distribution tag (used in RPM filenames)")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="keep temporary files")
    argcomplete.autocomplete(parser)
    return parser.parse_known_args(argv)


def setup_tmp_area():
    """
    Create temporary working area
    """
    tmp_dirpath = tempfile.mkdtemp()
    tmp_specs = os.path.join(tmp_dirpath, 'SPECS')
    tmp_build = os.path.join(tmp_dirpath, '_build')
    tmp_sources = os.path.join(tmp_build, 'SOURCES')

    os.makedirs(tmp_specs)
    os.makedirs(tmp_build)
    os.makedirs(tmp_sources)

    return (tmp_dirpath, tmp_specs, tmp_sources)


def extract_topdir(tmp_specfile, source):
    """
    Set the topdir name taken from the source tarball
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if 'autosetup' in line:
            tar = tarfile.open(source)
            topname = os.path.commonprefix(tar.getnames())
            if topname in tar.getnames():
                top_element = tar.getmember(topname)
                if top_element.isdir():
                    print "%s -n %s" % (line.strip(), topname)
            else:
                print "%s -c" % line.strip()
        else:
            print line,


def get_command_line(intercepted_args, tmp_sources, tmp_specfile):
    """
    Return rpmbuild command line and arguments
    """
    cmd = ['rpmbuild']
    if intercepted_args.quiet:
        cmd.append('--quiet')
    if intercepted_args.topdir is not None:
        cmd.append('--define')
        cmd.append('_topdir %s' % intercepted_args.topdir)
    if intercepted_args.dist is not None:
        cmd.append('--define')
        cmd.append('%%dist %s' % intercepted_args.dist)
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmp_sources)
    cmd.append('-bs')
    cmd.append(tmp_specfile)

    return cmd


def main(argv):
    """
    Entry point arguments: component.spec Source0 Source1 ... Patch0 Patch1 ...
    The specfile must always be present and it has to be the first in the list
    """
    if len(sys.argv) < 2:
        sys.exit("ERROR: You need to specify the component specfile")

    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    specfile = passthrough_args[0]
    tmp_dirpath, tmp_specs, tmp_sources = setup_tmp_area()
    tmp_specfile = os.path.join(tmp_specs, os.path.basename(specfile))

    try:
        # Copy files to temporary working area
        copyfile(specfile, tmp_specfile)
        tarball_filters = ['.tar.gz', '.tar.bz2']

        for source in passthrough_args[1:]:
            if any([ext in source for ext in tarball_filters]):
                extract_topdir(tmp_specfile, source)
                copyfile(source, os.path.join(tmp_dirpath, source))
            else:
                copyfile(source, os.path.join(tmp_dirpath, source))

        cmd = get_command_line(intercepted_args, tmp_sources, tmp_specfile)
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
        if not intercepted_args.keeptmp:
            rmtree(tmp_dirpath)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
