"""
planex-make-srpm: Wrapper around rpmbuild
"""
from __future__ import print_function

import sys
import subprocess
import fileinput
import os
import re
import shutil
import tarfile
import tempfile

import argparse
import argcomplete
import planex.cmd.args
from planex.spec import load
from planex.link import Link
from planex.tarball import Tarball


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Pack sources and patchqueues into a source RPM',
        parents=[planex.cmd.args.common_base_parser(),
                 planex.cmd.args.rpm_define_parser(),
                 planex.cmd.args.keeptmp_parser()])
    parser.add_argument("spec", metavar="SPEC", help="Spec file")
    parser.add_argument("sources", metavar="SOURCE/PATCHQUEUE", nargs='*',
                        help="Source and patchqueue files")
    argcomplete.autocomplete(parser)

    parsed_args = parser.parse_args(argv)
    links = [arg for arg in argv
             if arg.endswith(".lnk") or arg.endswith(".pin")]
    parsed_args.link = None
    if links:
        parsed_args.link = Link(links[0])

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
        cmd.append(" ".join(define))
    cmd.append('--define')
    cmd.append('_sourcedir %s' % tmpdir)
    cmd.append('-bs')
    cmd.append(specfile)

    return subprocess.call(cmd)


def get_commit_id(info_file):
    """
    Read the commit id from the .gitarchive-info file
    """
    regex = re.compile(r'^Changeset: (.*)$')
    for line in info_file:
        match = regex.match(line)
        if match:
            changeset = match.group(1)
            # Skip if .gitarchive-info hasn't passed through `git archive`
            # rpm chokes in the following way:
            #   Illegal char '$' in: Provides: gitsha(source.tar) = $Format:%H$
            if changeset.startswith("$Format"):
                continue
            return changeset
    return None


def add_gitsha_provides(manifests):
    """
    Add the source line and additional provides to the current location
    """
    for key in manifests:
        print('Provides: gitsha({0}) = {1}'.format(key, manifests[key]))


def add_manifest_entry(manifests, specfile):
    """
    Add provides entries to the specfile that show the manifest data
    """
    # Have to do this in two passes, find the highest source and then
    # add one higher
    source = re.compile(r'^Source0: .*$')
    for line in fileinput.input(specfile, inplace=True):
        print(line, end="")
        match = source.match(line)
        if match:
            add_gitsha_provides(manifests)


def extract_commit(source, manifests):
    """
    Try to extract git archive information from a source entry
    """
    if tarfile.is_tarfile(source):
        with Tarball(source) as tarball:
            try:
                archive_info = tarball.extractfile('.gitarchive-info')
                if archive_info:
                    name = os.path.basename(source)
                    origin_name = '{0}.origin'.format(source)
                    if os.path.exists(origin_name):
                        with open(origin_name, 'r') as origin_file:
                            name = origin_file.readline()
                    manifests[name.strip()] = get_commit_id(archive_info)
            except KeyError:
                pass


def populate_working_directory(tmpdir, spec):
    """
    Build a working directory containing everything needed to build the SRPM.
    """

    sources = [os.path.basename(source[0]) for source in spec.sources()]
    for source in sources:
        try:
            spec.extract_source(source, tmpdir)
        except KeyError:
            print("Could not find a source for %s" % source)

    newspec = os.path.join(tmpdir, os.path.basename(spec.specpath()))
    manifests = {}

    with open(newspec, "w") as out:
        out.writelines(spec.rewrite_spec())

    if manifests:
        add_manifest_entry(manifests, newspec)
    else:
        print("No .gitarchive-info found for {0}".format(spec.name()))

    return newspec


def main(argv=None):
    """
    Entry point
    """
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args_or_exit(argv)
    tmpdir = tempfile.mkdtemp(prefix="px-srpm-")

    try:
        spec = load(args.spec, args.link, defines=args.define)
        specfile = populate_working_directory(tmpdir, spec)
        sys.exit(rpmbuild(args, tmpdir, specfile))

    except (tarfile.TarError, tarfile.ReadError) as exc:
        print("Error when extracting patchqueue from tarfile")
        print("Exception: %s" % exc)

    finally:
        # Clean temporary area (unless debugging)
        if args.keeptmp:
            print("Working directory retained at %s" % tmpdir)
        else:
            shutil.rmtree(tmpdir)
