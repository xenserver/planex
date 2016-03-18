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
        "--dist", metavar="DIST", default="",
        help="distribution tag (used in RPM filenames)")
    argcomplete.autocomplete(parser)
    return parser.parse_known_args(argv)


def parse_patchseries(series_file):
    """
    Parse series file and return the list of patches
    """
    patches = []
    for line in open(series_file):
        line = line.strip()
        if not line.startswith("#"):
            patches.append(line)

    return patches


def setup_tmp_area():
    """
    Create temporary wotking area
    """
    tmp_dirpath = tempfile.mkdtemp() + '/'
    tmp_specs = tmp_dirpath + 'SPECS/'
    tmp_build = tmp_dirpath + '_build/'
    tmp_sources = tmp_build + 'SOURCES/'

    os.makedirs(tmp_specs)
    os.makedirs(tmp_build)
    os.makedirs(tmp_sources)

    return (tmp_dirpath, tmp_sources)


def main(argv):
    """
    Entry point arguments: component.spec Source0 Source1 ... Patch0 Patch1 ...
    The specfile must always be present and it has to be the first in the list
    """
    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    target = os.path.basename(passthrough_args[0]).split('.')[0]
    specfile = passthrough_args[0]
    tmp_dirpath, tmp_sources = setup_tmp_area()
    tmp_specfile = tmp_dirpath + specfile

    try:
        # Copy files to temporary working area
        copyfile(specfile, tmp_specfile)
        patchqueue = False
        patchqueue_path = None
        patchqueue_filters = ['.pg.', '.pq.']

        for source in passthrough_args[1:]:
            copyfile(source, tmp_dirpath + source)
            if any([ext in source for ext in patchqueue_filters]):
                patchqueue = True
                patchqueue_path = source

        if patchqueue:
            # Extract patches
            patch_num = 0
            for line in fileinput.input(tmp_specfile, inplace=True):
                if any([ext in line for ext in patchqueue_filters]):
                    tar = tarfile.open(tmp_dirpath + patchqueue_path)
                    for mem in tar.getmembers():
                        mem.name = '%s-' % target + os.path.basename(mem.name)
                        tar.extract(mem, tmp_sources)
                    patches = parse_patchseries(tmp_sources +
                                                '%s-series' % target)
                    print "# Patches for %s" % target
                    for patch in patches:
                        if patch != "":
                            print "Patch%s: %%{name}-%s" % (patch_num, patch)
                            patch_num += 1
                else:
                    print line,

        args = []
        if intercepted_args.quiet:
            args.append('--quiet')
        if intercepted_args.topdir is not None:
            args.append('--define')
            args.append('_topdir %s' % intercepted_args.topdir)
        if intercepted_args.dist != "":
            args.append('--define')
            args.append(u'%dist ' + intercepted_args.dist)
        args.append('--define')
        args.append('_sourcedir %s' % tmp_sources)
        args.append('-bs')
        args.append(tmp_specfile)
        cmd = ['rpmbuild']
        cmd.extend(args)

        return_value = subprocess.call(cmd)
        sys.exit(return_value)

    except Exception as inst:
        print type(inst)
        print inst.args
        print inst

    finally:
        # Clean temporary area
        rmtree(tmp_dirpath)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
