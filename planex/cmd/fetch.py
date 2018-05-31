"""
planex-fetch: Download sources referred to by a spec file
"""

import argparse
import logging
import os
import shutil
import sys

import argcomplete
import git
import pkg_resources
import requests
from requests.adapters import HTTPAdapter
from requests.adapters import Retry

# pylint: disable=relative-import
from six.moves.urllib.parse import urlparse, urlunparse

from planex.link import Link
from planex.cmd.args import common_base_parser, rpm_define_parser
from planex.repository import Repository
from planex.util import run
from planex.util import setup_logging
from planex.util import setup_sigint_handler
import planex.spec


# This should include all of the extensions in the Makefile.rules for fetch
SUPPORTED_EXT_TO_MIME = {
    '.tar': 'application/x-tar',
    '.gz': 'application/x-gzip',
    '.tgz': 'application/x-gzip',
    '.txz': 'application/x-gzip',
    '.bz2': 'application/x-bzip2',
    '.tbz': 'application/x-bzip2',
    '.zip': 'application/zip',
    '.pdf': 'application/pdf',
    '.patch': 'text/x-diff'
}

SUPPORTED_URL_SCHEMES = ["http", "https"]


def requests_retry_session(retries):
    """Return a requests session that will try the download [retries] times"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class FetchVerifyError(Exception):
    """Exception thrown by the best_effort_file_verify function"""
    pass


def best_effort_file_verify(path):
    """
    Given a path, check if the file at that path has a sensible format.
    If the file has an extension then it checks that the mime-type of this file
    matches that of the file extension as defined by the IANA:
        http://www.iana.org/assignments/media-types/media-types.xhtml
    """
    _, ext = os.path.splitext(path)
    if ext and ext in SUPPORTED_EXT_TO_MIME:
        # output of `file` is of form: "<path>: <mime-type>"
        cmd = ["file", "--mime-type", path]
        stdout = run(cmd, check=False)['stdout'].strip()
        _, _, mime_type = stdout.partition(': ')

        if SUPPORTED_EXT_TO_MIME[ext] != mime_type:
            raise FetchVerifyError(
                "%s: Fetched file format looks incorrect: %s: %s" %
                (sys.argv[0], path, mime_type))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources',
                                     parents=[common_base_parser(),
                                              rpm_define_parser()])
    parser.add_argument('spec', help='RPM Spec')
    parser.add_argument('link', help='Link file', nargs="?")
    parser.add_argument("source", metavar="SOURCE",
                        help="Source file to fetch")
    parser.add_argument('--retries', '-r',
                        help='Number of times to retry a failed download',
                        type=int, default=5)
    parser.add_argument('--no-package-name-check', dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def write_originfile(name, url, sha=None):
    """
    Write "[url]\n[sha]\n" in [name].origin for tracking
    """
    if sha is None:
        sha = ""
    content = "{}\n{}\n".format(url, sha)
    with open('{0}.origin'.format(name), 'w') as origin_file:
        origin_file.write(content)


def fetch_http(url, filename, retries):
    """
    Download the file at url and store it as filename
    """

    url_string = urlunparse(url)
    logging.debug("Fetching %s to %s", url_string, filename)

    useragent = "planex-fetch/%s" % pkg_resources.require("planex")[0].version

    # We need this because centos ships requests 2.8.0
    # It can be greatly simplified with requests >= 2.18.0
    headers = requests.utils.default_headers()
    headers.update({
        "user-agent": useragent,
    })

    # Once we use requests >= 2.18.0, we should change this into
    # with requests.get ... as r:
    req = requests_retry_session(retries).get(
        url_string, headers=headers, timeout=30, stream=True)
    req.raise_for_status()

    with open(filename, 'wb') as out:
        shutil.copyfileobj(req.raw, out)
    best_effort_file_verify(filename)

    # pylint: disable=W0703
    # best-effort get git commitish
    try:
        repo = Repository(url_string)
        sha = repo.sha1
    except Exception:
        sha = None

    write_originfile(filename, url_string, sha)


def fetch_url(url, source, retries):
    """Fetch from specified URL"""
    try:
        fetch_http(url, source, retries)

    except requests.RequestException as exn:
        # Download failed
        sys.exit("%s: Failed to fetch %s: %s" %
                 (sys.argv[0], urlunparse(url), exn.args[1]))

    except IOError as exn:
        # IO error saving source file
        sys.exit("%s: %s: %s" %
                 (sys.argv[0], exn.strerror, exn.filename))

    except FetchVerifyError as exn:
        # MIME type mismatch
        sys.exit(exn.message)


def fetch_repo(url, resource):
    """Git archive from local git repo"""
    reponame = os.path.basename(url.path).rsplit(".git")[0]
    repo = git.Repo(os.path.join("repos", reponame))
    with open(resource.path, "wb") as output:
        if resource.prefix is not None:
            prefix = str(resource.prefix)
        else:
            prefix = None
        repo.archive(output, treeish=str(resource.commitish),
                     prefix=prefix)

    try:
        ref = repo.refs[str(resource.commitish)]
        sha = ref.object.hexsha
    except (IndexError, AttributeError):
        sha = None

    write_originfile(resource.path, repo.remotes.origin.url, sha)


def fetch_source(args):
    """
    Download requested source using URL from spec file.
    """

    link = None
    if args.link:
        link = Link(args.link)

    spec = planex.spec.load(args.spec, link=link,
                            check_package_name=args.check_package_names,
                            defines=args.define)

    try:
        resource = spec.resource(args.source)
    except KeyError as exn:
        sys.exit("%s: No source corresponding to %s" % (sys.argv[0], exn))

    url = urlparse(resource.url)
    if url.scheme in SUPPORTED_URL_SCHEMES:
        fetch_url(url, resource.path, args.retries + 1)

    elif url.scheme == 'ssh':
        fetch_repo(url, resource)

    elif url.scheme in ['', 'file'] and url.netloc == '':
        shutil.copyfile(url.path, resource.path)
        write_originfile(resource.path, url.path)

    else:
        sys.exit("%s: Unsupported url scheme %s" %
                 (sys.argv[0], url.scheme))


def main(argv=None):
    """
    Main function.  Fetch sources directly or via a link file.
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    fetch_source(args)
