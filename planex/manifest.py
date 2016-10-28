#!/usr/bin/env python

"""
planex-manifest: Generate manifest in JSON format from spec/link files.

Every invocation prints the manifest for a single package in stdout.
"""

import json
import argparse
import argcomplete

from planex.util import add_common_parser_options
from planex.spec import Spec
from planex.repository import Repository


def parse_cmdline():
    """Parse command line options"""

    parser = argparse.ArgumentParser(
        description='Generate manifest in JSON format from spec/link files'
    )

    add_common_parser_options(parser)

    parser.add_argument(
        'specfile_path',
        metavar='SPEC',
        help='path/to/<spec_file>'
    )

    parser.add_argument(
        'lnkfile_path',
        metavar='LNK',
        nargs='?',
        default=None,
        help='path/to/<lnk_file>'
    )

    argcomplete.autocomplete(parser)
    return parser.parse_args()


def get_path(package_name):
    """Get relative path to manifest file for package."""
    return './MANIFESTS/{}.json'.format(package_name)


def generate_manifest(spec, link=None):
    """Record info of all remote sources in the spec/link files.

    Args:
        spec (planex.spec.Spec): package's spec file
        link (dict/None): package's link file, if applicable

    Returns:
        (dict): manifest of the remote sources
                needed to create the SRPM.
        Format:
        {
            "spec": {
                "source0": {
                    "url": <source0_url>,
                    "sha1": <source0_sha1>
                },
                "source1": ...
                .
                .
            },
            "lnk": {
                "url": <lnk_url>,
                "sha1": <lnk_sha1>
            }
        }
    """
    branch = None

    if link is not None:
        branch = link.get('branch')

    manifest = {'spec': {}}
    source_urls = [url for url in spec.source_urls() if '://' in url]

    for i, url in enumerate(source_urls):
        if branch:
            url = url.replace("%{branch}", branch)

        # Sources taken from artifactory do not have SHA1
        if 'repo.citrite.net' not in url:
            repo_ref = Repository(url)
            sha1 = repo_ref.sha1
        else:
            sha1 = None

        manifest['spec']['source' + str(i)] = {'url': url, 'sha1': sha1}

    if link is not None:
        repo_ref = Repository(link['URL'])
        sha1 = repo_ref.sha1
        manifest['lnk'] = {'url': link['URL'], 'sha1': sha1}

    return manifest


def main():
    """Entry point."""

    args = parse_cmdline()

    spec = Spec(args.specfile_path)

    if args.lnkfile_path is not None:
        with open(args.lnkfile_path) as link_fh:
            link = json.load(link_fh)
    else:
        link = None

    manifest = generate_manifest(spec, link)
    print json.dumps(manifest, indent=4)


if __name__ == '__main__':
    main()
