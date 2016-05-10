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
    argcomplete.autocomplete(parser)
    return parser.parse_known_args(argv)


def parse_patchseries(series_file):
    """
    Parse series file and return the list of patches
    """
    patches = []
    with open(series_file) as series:
        for line in series:
            line = line.partition('#')[0].strip()
            if line:
                patches.append(line)

    return patches


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


def extract_patches(tmp_specfile, patchqueue_filters, patchqueue_path,
                    tmp_sources, target):
    """
    Extract patches and inject them into the specfile
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if any([ext in line for ext in patchqueue_filters]):
            tar = tarfile.open(patchqueue_path)
            for mem in tar.getmembers():
                # Modify mem.name in place to change the name of the
                # extracted file (and drop any leading paths)
                mem.name = '%s-' % target + os.path.basename(mem.name)
                tar.extract(mem, tmp_sources)
            patches = parse_patchseries(os.path.join(tmp_sources,
                                                     '%s-series' % target))
            print "# Patches for %s" % target
            for patch_num, patch in enumerate(patches):
                if patch:
                    print "Patch%s: %%{name}-%s" % (patch_num, patch)
        else:
            print line,


def extract_topdir(tmp_specfile, source):
    """
    Set the topdir name taken from the source tarball
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if 'autosetup' in line:
            tar = tarfile.open(source)
            topname = os.path.commonprefix(tar.getnames())
            print "%s -n %s" % (line.strip(), topname)
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


def extract_patches(tmp_specfile, patchqueue_filters, patchqueue_path,
                    tmp_sources, target):
    """
    Extract patches and inject them into the specfile
    """
    for line in fileinput.input(tmp_specfile, inplace=True):
        if any([ext in line for ext in patchqueue_filters]):
            tar = tarfile.open(patchqueue_path)
            for mem in tar.getmembers():
                # Modify mem.name in place to change the name of the
                # extracted file (and drop any leading paths)
                mem.name = '%s-' % target + os.path.basename(mem.name)
                tar.extract(mem, tmp_sources)
            patches = parse_patchseries(os.path.join(tmp_sources,
                                                     '%s-series' % target))
            print "# Patches for %s" % target
            for patch_num, patch in enumerate(patches):
                if patch:
                    print "Patch%s: %%{name}-%s" % (patch_num, patch)
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
    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    target = os.path.splitext(os.path.basename(passthrough_args[0]))[0]
    specfile = passthrough_args[0]
    tmp_dirpath, tmp_specs, tmp_sources = setup_tmp_area()
    tmp_specfile = os.path.join(tmp_specs, os.path.basename(specfile))

    try:
        # Copy files to temporary working area
        copyfile(specfile, tmp_specfile)
        patchqueue_filters = ['.pg.', '.pq.']
        tarball_filters = ['.tar.gz', '.tar.bz2']

        for source in passthrough_args[1:]:
            if any([ext in source for ext in patchqueue_filters]):
                extract_patches(tmp_specfile, patchqueue_filters,
                                source, tmp_sources, target)
            elif any([ext in source for ext in tarball_filters]):
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
