"""
planex-clone-sources: Checkout sources referred to by a spec (and link) file
"""

import argparse
import json
import os
import os.path
import subprocess
import sys
import urlparse

import argcomplete

import planex.repository
import planex.spec
from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler


def checkout_patchqueue(topdir, linkname, dryrun):
    """
    Clone a patchqueue repository referred to in the link URL
    """
    try:
        with open(linkname) as fileh:
            link = json.load(fileh)

    except IOError as exn:
        # IO error loading JSON file
        sys.exit("%s: %s: %s" %
                 (sys.argv[0], exn.strerror, exn.filename))

    repo = planex.repository.Repository(link['URL'])
    if dryrun:
        print repo
    else:
        repo.clone(topdir, dirname='patches')


def checkout_remote_source(topdir, specname, dryrun):
    """
    Clone the respositories referred to in the source URLs
    """
    repos = []
    spec = planex.spec.Spec(specname, check_package_name=False)
    for url_str in spec.source_urls():
        url = urlparse.urlparse(url_str)
        if url.netloc != '':
            repo = planex.repository.Repository(url_str)
            if dryrun:
                print repo
            else:
                repo.clone(topdir)
            repos.append(repo)
    return repos


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Clone package sources')
    add_common_parser_options(parser)
    parser.add_argument('specfile', help='RPM spec file')
    parser.add_argument("-t", "--topdir", metavar="DIR", required=True,
                        help='Set toplevel directory')
    parser.add_argument("-l", "--linkfile",
                        help='Link file')
    parser.add_argument("-d", "--dryrun", action='store_true',
                        help='Just report repositories')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function.  Check out sources defined in a spec file.
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)

    repos = checkout_remote_source(args.topdir, args.specfile, args.dryrun)
    if args.linkfile:
        base_dir = os.path.join(args.topdir, repos[0].dir_name)
        patch_dir = os.path.join(base_dir, '.git')
        checkout_patchqueue(patch_dir, args.linkfile, args.dryrun)
        if not args.dryrun:
            # Create empty guilt status for the branch
            status = os.path.join(patch_dir, 'patches', repos[0].branch,
                                  'status')
            fileh = open(status, 'w')
            fileh.close()
            subprocess.check_call(['guilt', 'push', '--all'], cwd=base_dir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
