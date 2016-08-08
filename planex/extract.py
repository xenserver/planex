"""
planex-extract: Extract files from a tarball as described by a link file
"""

import argparse
import json
import logging
import os
import os.path
import re
import sys
import tarfile

from contextlib import closing

import argcomplete

from planex.util import add_common_parser_options
from planex.util import setup_logging
from planex.util import setup_sigint_handler
import planex.spec


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


def parse_patchseries(series, guard=None):
    """
    Parse series file and return the list of patches
    """
    guard_re = re.compile(r'([\S]+)(\s#.*)?')

    for line in series:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = guard_re.match(line)
        if match.group(2):
            gtype = match.group(2)[2]
            guard_patch = match.group(2)[3:]

            if gtype == '+' and guard != guard_patch:
                continue
            if gtype == '-' and guard == guard_patch:
                continue

        yield match.group(1)


def rewrite_spec(spec_in, spec_out, patches, patchnum):
    """
    Expand a patchqueue as a sequence of patches in a spec file
    """
    done = False
    with open(spec_in) as fh_in:
        with open(spec_out, 'w') as fh_out:
            for line in fh_in:
                if not done and line.upper().startswith('SOURCE'):
                    for patch in patches:
                        patchnum += 1
                        fh_out.write("Patch%d: %s\n" % (patchnum, patch))
                    done = True
                fh_out.write(line)


def expand_patchqueue(args, tar, seriesfile):
    """
    Create a list of patches from a patchqueue and update the spec file
    """
    # Build a list of patches
    with closing(tar.extractfile(seriesfile)) as series:
        patches = list(parse_patchseries(series))

    spec = planex.spec.Spec(args.output, topdir=args.topdir,
                            check_package_name=args.check_package_names)
    patchnum = spec.highest_patch()

    # Rewrite the spec file to include the patches
    rewrite_spec(args.output, args.output + ".new", patches, patchnum)

    # Switch extracted spec file with new specfile
    os.rename(args.output, args.output + ".old")
    os.rename(args.output + ".new", args.output)


def archive_root(tar):
    """
    Return the name of the top level directory of the tarball
    """
    if tar.firstmember.type == tarfile.DIRTYPE:
        return tar.firstmember.name
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
    parser.add_argument("-t", "--topdir", metavar="DIR", default=None,
                        help="Set rpmbuild toplevel directory")
    parser.add_argument("--no-package-name-check", dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
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
                     args.output)

        if 'patchqueue' in link:
            patch_dir = os.path.join(tar_root, str(link['patchqueue']))
            expand_patchqueue(args, tar, os.path.join(patch_dir, 'series'))
        elif 'patches' in link:
            patch_dir = os.path.join(tar_root, str(link['patches']))
        else:
            sys.exit("%s: %s: Expected one of 'patchqueue' or 'patches'" %
                     (sys.argv[0], args.link))

        # Extract sources contained in the tarball
        spec = planex.spec.Spec(args.output, topdir=args.topdir,
                                check_package_name=args.check_package_names)
        for path, url in spec.all_sources():
            if url.netloc == '':
                src_path = os.path.join(patch_dir, url.path)
                if src_path not in tar.getnames():
                    src_path = os.path.join(tar_root, url.path)
                extract_file(tar, src_path, path)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
