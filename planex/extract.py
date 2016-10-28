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
    os.utime(name_out, None)


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


def rewrite_spec(spec_in, spec_fh, patches, patchnum):
    """
    Expand a patchqueue as a sequence of patches in a spec file
    """
    done = False
    with open(spec_in) as fh_in:
        for line in fh_in:
            if not done and line.upper().startswith('SOURCE'):
                for patch in patches:
                    patchnum += 1
                    spec_fh.write("Patch%d: %%{name}-%s\n" %
                                  (patchnum, patch))
                done = True
            spec_fh.write(line)


def expand_patchqueue(spec_fh, spec, spec_in, tar, seriesfile):
    """
    Create a list of patches from a patchqueue and update the spec file
    """
    # Build a list of patches
    with closing(tar.extractfile(seriesfile)) as series:
        patches = list(parse_patchseries(series))

    patchnum = spec.highest_patch()

    # Rewrite the spec file to include the patches
    rewrite_spec(spec_in, spec_fh, patches, patchnum)


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
    parser.add_argument("--no-package-name-check", dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    parser.add_argument("-D", "--define", default=[], action="append",
                        help="--define='MACRO EXPR' define MACRO with "
                        "value EXPR")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function.  Fetch sources directly or via a link file.
    """
    # pylint: disable=R0914

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
            check_names = args.check_package_names
            spec = planex.spec.Spec(args.output + '.tmp',
                                    check_package_name=check_names,
                                    defines=macros)

            if 'branch' in link:
                spec_fh.write("%%define branch %s\n" % link['branch'])

            if 'patchqueue' in link:
                patch_dir = os.path.join(tar_root, str(link['patchqueue']))
                expand_patchqueue(spec_fh, spec, args.output + '.tmp',
                                  tar, os.path.join(patch_dir, 'series'))
            elif 'patches' in link:
                patch_dir = os.path.join(tar_root, str(link['patches']))
                copy_spec(args.output + '.tmp', spec_fh)
            else:
                sys.exit("%s: %s: Expected one of 'patchqueue' or 'patches'" %
                         (sys.argv[0], args.link))

        # Extract sources contained in the tarball
        spec = planex.spec.Spec(args.output,
                                check_package_name=args.check_package_names,
                                defines=macros)
        for path, url in spec.all_sources():
            if url.netloc == '':
                if 'patchqueue' in link:
                    # trim off prefix
                    src_path = os.path.join(patch_dir,
                                            url.path[len(spec.name()) + 1:])
                else:
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
