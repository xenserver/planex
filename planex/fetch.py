"""
planex-fetch: Download sources referred to by a spec file
"""

import argparse
import argcomplete
import os
import shutil
import planex.spec
import urlparse
import pycurl
import sys
import logging
import pkg_resources
from planex.util import setup_sigint_handler
from planex.util import add_common_parser_options
from planex.util import setup_logging


def curl_get(url_string, out_file):
    """
    Fetch the contents of url and store to file represented by out_file
    """
    curl = pycurl.Curl()

    # General options
    useragent = "planex-fetch/%s" % pkg_resources.require("planex")[0].version
    curl.setopt(pycurl.USERAGENT, useragent)
    curl.setopt(pycurl.FOLLOWLOCATION, True)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.FAILONERROR, True)

    # Cribbed from /usr/lib64/python2.6/site-packages/curl/__init__.py
    curl.setopt(pycurl.SSL_VERIFYHOST, 2)
    curl.setopt(pycurl.COOKIEFILE, "/dev/null")
    curl.setopt(pycurl.NETRC, 1)
    # If we use threads, we should also set NOSIGNAL and ignore SIGPIPE

    # Set URL to fetch and file to which to write the response
    curl.setopt(pycurl.URL, url_string)
    curl.setopt(pycurl.WRITEDATA, out_file)

    try:
        curl.perform()
    finally:
        curl.close()


def make_dir(path):
    """
    Ensure that path exists
    """
    if not os.path.isdir(path):
        os.makedirs(path)


def fetch_http(url, filename, retries):
    """
    Download the file at url and store it as filename
    """

    while True:
        retries -= 1
        try:
            url_string = urlparse.urlunparse(url)
            logging.debug("Fetching %s to %s", url_string, filename)

            make_dir(os.path.dirname(filename))
            tmp_filename = filename + "~"
            with open(tmp_filename, "wb") as tmp_file:
                curl_get(url_string, tmp_file)
                shutil.move(tmp_filename, filename)
                return

        except pycurl.error as exn:
            logging.debug(exn.args[1])
            if not retries > 0:
                raise


def all_sources(spec, topdir, check_package_names):
    """
    Get all source URLs defined in the spec file
    """
    spec = planex.spec.Spec(spec, topdir=topdir,
                            check_package_name=check_package_names)
    urls = [urlparse.urlparse(url) for url in spec.source_urls()]
    return zip(spec.source_paths(), urls)


def check_valid_protocol(url):
    if url.scheme and url.scheme not in ["http", "https", "file"]:
        sys.exit("%s: Unimplemented protocol: %s" %
                 (sys.argv[0], url.scheme))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources')
    add_common_parser_options(parser)
    parser.add_argument('spec', help='RPM Spec file')
    parser.add_argument('--retries', '-r',
                        help='Number of times to retry a failed download',
                        type=int, default=5)
    parser.add_argument("-t", "--topdir", metavar="DIR", default=None,
                        help='Set rpmbuild toplevel directory')
    parser.add_argument('--no-package-name-check', dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    for path, url in all_sources(args.spec, args.topdir,
                                 args.check_package_names):
        check_valid_protocol(url)
        if url.scheme in ["http", "https", "file"]:
            try:
                fetch_http(url, path, args.retries + 1)

            except pycurl.error as exn:
                # Curl download failed
                sys.exit("%s: Failed to fetch %s: %s" %
                         (sys.argv[0], urlparse.urlunparse(url), exn.args[1]))

            except IOError as exn:
                # IO error saving source file
                sys.exit("%s: %s: %s" %
                         (sys.argv[0], exn.strerror, exn.filename))

        elif url.scheme == '' and os.path.dirname(url.path) == '':
            if not os.path.exists(path):
                sys.exit("%s: Source not found: %s" % (sys.argv[0], path))

            # Source file is pre-populated in the SOURCES directory (part of
            # the repository - probably a patch or local include).   Update
            # its timestamp to placate make, but don't try to download it.
            logging.debug("Refreshing timestamp for local source %s", path)
            os.utime(path, None)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
