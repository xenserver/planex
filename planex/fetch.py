"""
planex-fetch: Download sources referred to by a spec file
"""

import argparse
import os
import planex.spec
import urlparse
import pycurl
import sys
import logging
import pkg_resources


def curl_get(url, out_file):
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
    url_string = urlparse.urlunparse(url)
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
            logging.info("Fetching %s to %s", url, filename)

            make_dir(os.path.dirname(filename))
            with open(filename, "wb") as out_file:
                curl_get(url, out_file)
                return

        except pycurl.error as exn:
            logging.info(exn.args[1])
            if not retries > 0:
                raise


def url_for_source(spec, source):
    """
    Find the URL corresponding to source in the spec file
    """
    spec = planex.spec.Spec(spec)
    source_basename = os.path.basename(source)

    for path, url in zip(spec.source_paths(), spec.source_urls()):
        if path.endswith(source_basename):
            return urlparse.urlparse(url)

    raise KeyError(source_basename)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources')
    parser.add_argument('spec', help='RPM Spec file')
    parser.add_argument('source', help='Source file')
    parser.add_argument('--verbose', '-v', help='Be verbose',
                        action='store_true')
    parser.add_argument('--retries', '-r',
                        help='Number of times to retry a failed download',
                        type=int, default=5)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    args = parse_args_or_exit(argv)
    if args.verbose:
        logging.basicConfig(format='%(message)s', level=logging.INFO)

    try:
        url = url_for_source(args.spec, args.source)
    except KeyError as exn:
        # Source file doesn't exist in the spec
        sys.exit("%s: No source corresponding to %s" % (sys.argv[0], exn))

    if url.scheme in ["http", "https", "file"]:
        try:
            fetch_http(url, args.source, args.retries + 1)
        except pycurl.error as exn:
            # Curl download failed
            sys.exit("%s: Failed to fetch %s: %s" %
                     (sys.argv[0], url, exn.args[1]))
        except IOError as exn:
            # IO error saving source file
            sys.exit("%s: %s: %s" % (sys.argv[0], exn.strerror, exn.filename))

    elif url.scheme == '' and os.path.dirname(url.path) == '' and \
            os.path.exists(args.source):
        # Source file is pre-populated in the SOURCES directory (part of the
        # repository - probably a patch or local include).   Update its
        # timestamp to placate make, but don't try to download it.
        logging.info("Refreshing timestamp for local source %s", args.source)
        os.utime(args.source, None)

    else:
        sys.exit("%s: Unimplemented protocol: %s" % (sys.argv[0], url.scheme))


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
