"""
planex-manifest: Generate manifest in JSON format from spec/link files.

Every invocation prints the manifest for a single package in stdout.
"""
from __future__ import print_function

import argparse
import json
import os

import argcomplete

from planex.cmd.args import common_base_parser
from planex.util import setup_logging
from planex.link import Link
from planex.spec import Spec
from planex.repository import Repository


def parse_args_or_exit(argv=None):
    """Parse command line options"""

    parser = argparse.ArgumentParser(
        description='Generate manifest in JSON format from spec/link files',
        parents=[common_base_parser()]
    )

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

    parser.add_argument(
        '--pins-dir',
        dest='pinsdir',
        default="PINS",
        help='path/to/pins'
    )

    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def get_path(package_name):
    """Get relative path to manifest file for package."""
    return '_build/MANIFESTS/{}.json'.format(package_name)


def get_name(spec_path, link_path):
    """Get the package name from the link and spec files path."""
    if link_path is not None:
        path = link_path
    else:
        path = spec_path
    name, _ = os.path.splitext(os.path.basename(path))
    return name


def update_with_schema_version_2(manifest, link):
    """Update spec with a schemaVersion 2 link"""

    for name, value in link.patch_sources.items():
        repo_ref = Repository(value["URL"])
        sha1 = repo_ref.sha1

        manifest["archives"][name] = {
            "url": value["URL"],
            "commitish": value.get("commitish"),
            "prefix": value.get("patches"),
            "sha1": sha1
        }

    for name, value in link.patchqueue_sources.items():
        repo_ref = Repository(value["URL"])
        sha1 = repo_ref.sha1
        manifest["patchqueues"][name] = {
            "url": value["URL"],
            "commitish": value.get("commitish"),
            "prefix": value.get("patchqueue"),
            "sha1": sha1
        }


def update_with_schema_version_3(manifest, link):
    """Update spec with a schemaVersion 3 link"""

    for name, value in link.sources.items():
        repo_ref = Repository(value["URL"])
        sha1 = repo_ref.sha1
        manifest["sources"][name] = {
            "url": value["URL"],
            "commitish": value.get("commitish"),
            "prefix": value.get("prefix"),
            "sha1": sha1
        }

    for name, value in link.archives.items():
        repo_ref = Repository(value["URL"])
        sha1 = repo_ref.sha1
        manifest["archives"][name] = {
            "url": value["URL"],
            "commitish": value.get("commitish"),
            "prefix": value.get("patches"),
            "sha1": sha1
        }

    for name, value in link.patchqueue_sources.items():
        repo_ref = Repository(value["URL"])
        sha1 = repo_ref.sha1
        manifest["patchqueues"][name] = {
            "url": value["URL"],
            "commitish": value.get("commitish"),
            "prefix": value.get("patches"),
            "sha1": sha1
        }


def generate_manifest(spec, link=None, pin=None):
    """Record info of all remote sources in the spec/link files.

    Args:
        spec (planex.spec.Spec): package's spec file
        link (dict/None): package's link file, if applicable

    Returns:
        (dict): manifest of the remote sources
                needed to create the SRPM.
        Format:
        {
            "sources": {
                "source0": {
                    "url": <source0_url>,
                    "sha1": <source0_sha1>
                },
                "source1": ...
                .
                .
            },
            "archives": {
                "url": <lnk_url>,
                "sha1": <lnk_sha1>
            },
            "pin": {
                "url": <pin_url>,
                "sha1": <pin_sha1>
            }
        }
    """

    manifest = {
        'spec': {},
        'sources': {},
        'archives': {},
        'patchqueues': {}
    }
    source_urls = [url for (_, url) in spec.sources() if '://' in url]

    for i, url in enumerate(source_urls):
        # Sources taken from artifactory do not have SHA1
        if 'repo.citrite.net' not in url:
            repo_ref = Repository(url)
            sha1 = repo_ref.sha1
        else:
            sha1 = None

        manifest['spec']['source' + str(i)] = {'url': url, 'sha1': sha1}

    if pin is not None:
        link = Link(pin)

    if link is not None:
        if link.schema_version == 2:
            update_with_schema_version_2(manifest, link)
        else:
            update_with_schema_version_3(manifest, link)

    return manifest


def main(argv=None):
    """Entry point."""

    args = parse_args_or_exit(argv)
    setup_logging(args)

    spec = Spec(args.specfile_path)

    link = None
    if args.lnkfile_path is not None:
        link = Link(args.lnkfile_path)

    pin = None
    pinfile = "{}/{}.pin".format(
        args.pinsdir,
        get_name(args.specfile_path, args.lnkfile_path)
    )
    if os.path.exists(pinfile):
        pin = pinfile

    manifest = generate_manifest(spec, link, pin)
    print(json.dumps(manifest, indent=4))
