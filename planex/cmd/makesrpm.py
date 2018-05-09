"""
planex-make-srpm: Wrapper around rpmbuild
"""
from __future__ import print_function

import sys
import subprocess
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
    parser.add_argument("--metadata", dest="metadata",
                        action="store_true",
                        help="Add inline comments in the spec file "
                        "to specify what provided sources, patches "
                        "and patchqueues")
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


def extract_commit(source):
    """
    Try to extract git archive information from a source entry
    """
    origin_name = '{0}.origin'.format(source)
    if not os.path.exists(origin_name):
        return (None, None)

    with open(origin_name, 'r') as origin_file:
        url = origin_file.readline().strip()
        # Note: sha is the empty string if EOF
        sha = origin_file.readline().strip()

    # .gitarchive-info wins over everything else
    if tarfile.is_tarfile(source):
        with Tarball(source) as tarball:
            try:
                archive_info = tarball.extractfile('.gitarchive-info')
                if archive_info:
                    commitish = get_commit_id(archive_info)
                    return (url, commitish)
            except KeyError:
                print("No .gitarchive-info info found for {0}".format(source))

    if sha:
        return (url, sha)

    return (None, None)


def populate_working_directory(metadata, tmpdir, spec):
    """
    Build a working directory containing everything needed to build the SRPM.
    """

    sources = [os.path.basename(source[0]) for source in spec.sources()]
    try:
        skipped = spec.extract_sources(sources, tmpdir)
    except KeyError as err:
        print("Could not find a source for {}".format(err))
        skipped = set()

    if skipped:
        print("The following archives have been ignored: {}".format(skipped))

    newspec = os.path.join(tmpdir, os.path.basename(spec.specpath()))
    manifests = {
        url: sha
        for url, sha in [
            extract_commit(resource.path) for resource in spec.resources()
        ]
        if url is not None
    }
    srpm_sources = sources if metadata else None

    with open(newspec, "w") as out:
        out.writelines(
            spec.rewrite_spec(srpm_sources=srpm_sources, manifests=manifests))

    if not manifests:
        print("No manifest info found for {0}".format(spec.name()))

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
        specfile = populate_working_directory(args.metadata, tmpdir, spec)
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
