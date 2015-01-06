"""
planex-fetch: Download sources referred to by a spec file
"""

import argparse
import os
import planex.spec
import pycurl
import sys


def get(url_string, out_file):
    """
    Fetch the contents of url_string and store to file represented by out_file
    """
    curl = pycurl.Curl()

    # General options
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
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


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources')
    parser.add_argument('spec', help='RPM Spec file')
    parser.add_argument('source', help='Source file')
    parser.add_argument('--verbose', '-v', help='Be verbose',
                        action='store_true')
    return parser.parse_args(argv)


def url_for_source(spec, source):
    """
    Find the URL corresponding to source in the spec file
    """
    spec = planex.spec.Spec(spec)
    source_basename = os.path.basename(source)

    for path, url in zip(spec.source_paths(), spec.source_urls()):
        if url.endswith(source_basename):
            return url

    raise KeyError(source_basename)


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    args = parse_args_or_exit(argv)

    try:
	url = url_for_source(args.spec, args.source)

        if args.verbose:
            print "Fetching %s to %s" % (url, args.source)

        with open(args.source, "wb") as out_file:
            get(url, out_file)

    except KeyError as exn:
        sys.exit("%s: No source corresponding to %s" % (sys.argv[0], exn))

    except IOError as exn:
        sys.exit("%s: %s: %s" % (sys.argv[0], exn.strerror, exn.filename))

    except pycurl.error as exn:
        sys.exit("%s: %s" % (sys.argv[0], exn[1]))


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


"""
Entry point when run directly
"""
if __name__ == "__main__":
    _main()
