#!/usr/bin/python

"""
planex-cache: A caching wrapper around mock for building RPMs
"""

import argparse
import hashlib
import itertools
import logging
import os
import rpm
import shutil
import sys
import tempfile

import argcomplete
import yum

from planex import util

PLANEX_CACHE_SALT = "planex-cache-1"


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Cache package building')
    util.add_common_parser_options(parser)
    parser.add_argument(
        '--cachedirs', default='~/.planex-cache:/misc/cache/planex-cache',
        help='colon-separated cache search path')
    # Overridden mock arguments.  Help text taken directly from mock.
    parser.add_argument(
        '--configdir', default="/etc/mock",
        help='Change where config files are found')
    parser.add_argument(
        '--resultdir', help='path for resulting files to be put')
    parser.add_argument(
        '-r', '--root', default="default",
        help='chroot name/config file name default: default')
    argcomplete.autocomplete(parser)
    return parser.parse_known_args(argv)


RFC4880_HASHES = {
    1:  "MD5",
    2:  "SHA1",
    3:  "RIPEMD160",
    8:  "SHA256",
    9:  "SHA384",
    10: "SHA512",
    11: "SHA224"}


def setup_yumbase(yumbase):
    """
    Set up the YUM database.
    """
    # the following call creates a /var/tmp/yum-<username>-<random>
    # directory to use as a cache.   reuse=True makes yum check
    # for similarly-named directories and re-use them, which makes
    # dependency searching much faster. However, this causes breakage
    # for concurrent builds.

    yumbase.setCacheDir(force=True, reuse=True)
    yumbase.repos.populateSack(cacheonly=True)


def load_srpm_from_file(filename):
    """
    Load an RPM header from an SRPM file.
    """
    with open(filename) as srpm:
        return rpm.ts().hdrFromFdno(srpm.fileno())


def cache_locations(cachedirs, pkg_hash):
    """
    Return the cache path to the build products with the given hash
    """
    return [os.path.join(x, pkg_hash) for x in cachedirs]


def in_cache(cachedirs, pkg_hash):
    """
    Return true if build products with the given hash are in the cache
    """
    return any(os.path.isdir(x) for x in cache_locations(cachedirs, pkg_hash))


def add_to_cache(cachedirs, pkg_hash, build_dir):
    """
    Add the build products in build_dir to the cache
    """

    # Another racing build may have written this package into the cache
    # while we were building.  If that is the case, we don't have to do
    # anything.
    if in_cache(cachedirs, pkg_hash):
        logging.debug("binary package already cached, skipping")
        return

    cache_dir = cache_locations(cachedirs, pkg_hash)[0]
    cache_output_dir = os.path.join(cache_dir, "output")

    if not os.path.isdir(cache_output_dir):
        os.makedirs(cache_output_dir)

    for fname in os.listdir(build_dir):
        shutil.copy(os.path.join(build_dir, fname), cache_output_dir)

    logging.debug("copied to %s", cache_output_dir)


def get_from_specified_cache(cache_dir, resultdir):
    """
    Copy the build products in the specific location to resultdir
    """
    build_output = os.path.join(cache_dir, "output")

    if not os.path.isdir(resultdir):
        os.makedirs(resultdir)

    for cached_file in os.listdir(build_output):
        cached_file_path = os.path.join(build_output, cached_file)
        shutil.copy(cached_file_path, resultdir)

        try:
            os.utime(cached_file_path, None)
        except OSError:
            # Don't fail if we can't update the timestamp.
            # The cache might be mounted read-only, for example.
            pass


def get_from_cache(cachedirs, pkg_hash, resultdir):
    """
    Copy the build products specified by the hash to resultdir
    """
    possibilities = cache_locations(cachedirs, pkg_hash)
    logging.debug("Possible cache hits: %s" + ", ".join(possibilities))
    cache_dir = next(itertools.ifilter(os.path.isdir, possibilities), None)
    if cache_dir:
        get_from_specified_cache(cache_dir, resultdir)


def get_srpm_hash(srpm, yumbase):
    """
    Calculate the cache hash of srpm, including the hashes of its build
    dependencies.  Only the first layer of dependencies are hashed -
    as OCaml libraries are statically linked this should be sufficient.
    """
    pkg_hash = hashlib.md5()
    pkg_hash.update(PLANEX_CACHE_SALT)

    if srpm.filedigestalgo:
        digestalgo = RFC4880_HASHES[srpm.filedigestalgo]
        logging.debug("Hashes of SRPM contents (%s):", digestalgo)
    else:
        digestalgo = RFC4880_HASHES[1]
        logging.debug("Hashes of SRPM contents (defaulted to %s):", digestalgo)

    for name, digest in zip(srpm.filenames, srpm.filedigests):
        logging.debug("  %s: %s", name, digest)
        pkg_hash.update(digest)

    logging.debug("Build-time requirements:")
    for req in sorted(srpm.requires):
        try:
            pkgs = yumbase.pkgSack.returnNewestByNameArch(patterns=[req])
            for pkg in pkgs:
                algo, checksum, _ = pkg.returnChecksums()[0]
                logging.debug("  %s: %s (%s: %s)", req, pkg, algo, checksum)
                pkg_hash.update(checksum)

                yumbase.downloadHeader(pkg)
                hdr = pkg.returnLocalHeader()
                logging.debug("  File hashes (%s):", digestalgo)
                for name, digest in zip(hdr.filenames, hdr.filedigests):
                    logging.debug("    %s: %s", name, digest)
                    pkg_hash.update(digest)

        except yum.Errors.PackageSackError as pse:
            logging.debug("  %s", pse)

    logging.debug("Package hash: %s", pkg_hash.hexdigest())
    return pkg_hash.hexdigest()


def build_package(configdir, root, passthrough_args):
    """
    Spawn a mock process to build the package.   Some arguments
    are intercepted and rewritten, for instance --resultdir.
    """
    working_directory = tempfile.mkdtemp(prefix="planex-cache")
    logging.debug("Mock working directory: %s", working_directory)

    cmd = ["mock", "--configdir=%s" % configdir,
           "--root=%s" % root,
           "--resultdir=%s" % working_directory] + passthrough_args

    logfiles = [os.path.join(working_directory, "root.log"),
                os.path.join(working_directory, "build.log")]
    util.run(cmd, logfiles=logfiles)

    return working_directory


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    util.setup_sigint_handler()
    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    config = os.path.join(intercepted_args.configdir,
                          intercepted_args.root + ".cfg")

    # Initialize yum before setting up logging, because yum uses
    # logging with a different default loglevel.   This avoids
    # having yum print lots of irrelevant messages during startup.
    yum_config = util.load_mock_config(config)
    yumbase = util.get_yumbase(yum_config)
    setup_yumbase(yumbase)

    util.setup_logging(intercepted_args)

    srpm = load_srpm_from_file(passthrough_args[-1])
    pkg_hash = get_srpm_hash(srpm, yumbase)

    cachedirs = [os.path.expanduser(x) for x
                 in intercepted_args.cachedirs.split(':')]

    # Expand default resultdir as done in mock.backend.Root
    resultdir = intercepted_args.resultdir or \
        yum_config['resultdir'] % yum_config

    if not os.path.isdir(resultdir):
        os.makedirs(resultdir)

    # Rebuild if not available in the cache
    if not in_cache(cachedirs, pkg_hash):
        logging.debug("Cache miss - rebuilding")
        build_output = build_package(intercepted_args.configdir,
                                     intercepted_args.root, passthrough_args)
        try:
            add_to_cache(cachedirs, pkg_hash, build_output)
        except OSError:
            # If we can't cache the result, that's not a fatal error
            pass

        for cached_file in os.listdir(build_output):
            dest = os.path.join(resultdir, cached_file)

            if os.path.exists(dest):
                os.unlink(dest)
            shutil.move(os.path.join(build_output, cached_file), resultdir)
    else:
        get_from_cache(cachedirs, pkg_hash, resultdir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
