#!/usr/bin/python

"""
planex-make-srpm: Wrapper around rpmbuild
"""

import sys
import subprocess
import os
import shutil
import tarfile
import tempfile

import argparse
import argcomplete
from planex.util import add_common_parser_options
from planex.spec import Spec
from planex.link import Link
from planex.patchqueue import Patchqueue
from planex.tarball import extract_topdir
from planex.tarball import Tarball


def parse_args_or_exit(argv):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Pack sources and patchqueues into a source RPM')
    add_common_parser_options(parser)
    parser.add_argument("spec", metavar="SPEC", help="Spec file")
    parser.add_argument("sources", metavar="SOURCE/PATCHQUEUE", nargs='*',
                        help="Source and patchqueue files")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="keep temporary files")
    argcomplete.autocomplete(parser)

    parsed_args = parser.parse_args(argv)
    links = [arg for arg in argv if arg.endswith(".lnk")]
    parsed_args.link = None
    if links:
        parsed_args.link = links[0]

    patchqueues = [arg for arg in argv if arg.endswith("patches.tar")]
    parsed_args.patchqueue = None
    if patchqueues:
        parsed_args.patchqueue = patchqueues[0]

    return parsed_args


def rpmbuild(args, tmpdir, specfile):
    """
    Run rpmbuild on working directory
    """
    cmd = ['rpmbuild']
    if args.quiet:
        cmd.append('--quiet')
    for define in args.define:
        cmd.append('--define')
        cmd.append(define)
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmpdir)
    cmd.append('-bs')
    cmd.append(specfile)

    return subprocess.call(cmd)


def main(argv):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)
    tmpdir = tempfile.mkdtemp()
    tmp_specfile = os.path.join(tmpdir, os.path.basename(args.spec))

    link = None
    if args.link:
        link = Link(args.link)

    try:
        # Copy spec to working area
        shutil.copyfile(args.spec, tmp_specfile)

        # Copy sources to working area, rewriting spec as needed
        tarball_filters = ['.tar.gz', '.tar.bz2']
        for source in args.sources:
            if any([ext in source for ext in tarball_filters]):
                extract_topdir(tmp_specfile, source)
            shutil.copy(source, tmpdir)

        spec = Spec(tmp_specfile, check_package_name=False)

        # Expand patchqueue to working area, rewriting spec as needed
        if args.link and args.patchqueue:
            # Extract patches
            if link.patchqueue is not None:
                with Patchqueue(args.patchqueue,
                                branch=link.patchqueue) as patches:
                    patches.extract_all(tmpdir)
                    patches.add_to_spec(spec, tmp_specfile)

            # Extract non-patchqueue sources
            with Tarball(args.patchqueue) as tarball:
                if link.sources is not None:
                    tarball.extract_dir(link.sources, tmpdir)
                if link.patches is not None:
                    tarball.extract_dir(link.patches, tmpdir)

        sys.exit(rpmbuild(args, tmpdir, tmp_specfile))

    except (tarfile.TarError, tarfile.ReadError) as exc:
        print "Error when extracting patchqueue from tarfile"
        print "Exception: %s" % exc

    finally:
        # Clean temporary area (unless debugging)
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
