#!/usr/bin/python

"""
planex-cache: A caching wrapper around mock for building RPMs
"""

import argparse
import hashlib
import os
import rpm
import shutil
import subprocess
import sys
import tempfile
import yum

LOG_DEBUG = 5
LOG_INFO = 1
LOG_NONE = 0

LOGLEVEL = 3

def log(level, message):
    """Conditional logging function"""
    if level <= LOGLEVEL:
        print message


def log_debug(message):
    """Wrapper for debug logging"""
    log(LOG_DEBUG, message)


def log_info(message):
    """Wrapper for info-level logging"""
    log(LOG_INFO, message)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Cache package building')

    # Overridden mock arguments
    parser.add_argument('--configdir',
        help='Change where config files are found')
    parser.add_argument('--resultdir',
        help='path for resulting files to be put')
    parser.add_argument('-r', '--root',
        help='chroot name/config file name default: default')
    return parser.parse_known_args(argv)


RFC4880_HASHES = {
    1:  "MD5",
    2:  "SHA1",
    3:  "RIPEMD160",
    8:  "SHA256",
    9:  "SHA384",
    10: "SHA512",
    11: "SHA224"}


def load_mock_config(cfg):
    """
    Load the yum configuration from the mock configuration file
    Nasty, but this is how mock loads its configuration file...
    From /usr/sbin/mock
    """

    import mockbuild.util
    unprivUid = os.getuid()
    __VERSION__ = 1
    PKGPYTHONDIR = "/usr/lib/python2.7/site-packages/mockbuild"
    config_opts = mockbuild.util.setup_default_config_opts(unprivUid,
        __VERSION__, PKGPYTHONDIR)
    config_opts['config_paths'] = []
    config_opts['config_paths'].append(cfg)
    execfile(cfg)
    return config_opts


def get_yum(config):
    """
    Initialise the Yum library and return an object which can be
    used to query the package database
    """
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(config['yum.conf'])
        temp.flush()

        yumbase = yum.YumBase()
        yumbase.repos.disableRepo('*')
        yumbase.getReposFromConfigFile(temp.name)

        # the following call creates a /var/tmp/yum-<username>-<random>
        # directory to use as a cache.   reuse=True makes yum check
        # for similarly-named directories and re-use them, which makes
        # dependency searching much faster

	# much faster if we only enable our own repository
        yumbase.repos.disableRepo('*')
        yumbase.repos.enableRepo('mock')

        yumbase.setCacheDir(force=True, reuse=True)
        #yumbase.repos.populateSack(cacheonly=True)
    return yumbase


def load_srpm_from_file(filename):
    """
    Load an RPM header from an SRPM file.
    """
    with open(filename) as srpm:
        return rpm.ts().hdrFromFdno(srpm.fileno())

def cache_location(cache_basedir, pkg_hash):
    """
    Return the cache path to the build products with the given hash
    """
    return os.path.join(cache_basedir, pkg_hash)


def in_cache(cache_basedir, pkg_hash):
    """
    Return true if build products with the given hash are in the cache
    """
    return os.path.isdir(cache_location(cache_basedir, pkg_hash))


def add_to_cache(cache_basedir, pkg_hash, build_dir):
    """
    Add the build products in build_dir to the cache
    """
    cache_dir = cache_location(cache_basedir, pkg_hash)
    assert os.path.isdir(cache_basedir)
    assert not os.path.isdir(cache_dir)

    if not os.path.isdir(cache_basedir):
        os.makedirs(cache_basedir)

    shutil.move(build_dir, cache_dir)
    log_debug("moved to %s" % cache_dir)


def get_from_cache(cache_basedir, pkg_hash, resultdir):
    """
    Copy the build products specified by the hash to resultdir
    """
    cache_dir = cache_location(cache_basedir, pkg_hash)
    assert os.path.isdir(cache_dir)

    if not os.path.isdir(resultdir):
        os.makedirs(resultdir)

    for cached_file in os.listdir(cache_dir):
        shutil.copy(os.path.join(cache_dir, cached_file), resultdir)


def get_srpm_hash(srpm, yumbase):
    """
    Calculate the cache hash of srpm, including the hashes of its build
    dependencies.  Only the first layer of dependencies are hashed -
    as OCaml libraries are statically linked this should be sufficient.
    """
    pkg_hash = hashlib.md5()

    log_debug("Hashes of SRPM contents (%s):" %
        RFC4880_HASHES[srpm.filedigestalgo])
    for name, digest in zip(srpm.filenames, srpm.filedigests):
        log_debug("  %s: %s" % (name, digest))
        pkg_hash.update(digest)

    log_debug("Build-time requirements:")
    for req in sorted(srpm.requires):
        try:
            pkgs = yumbase.pkgSack.returnNewestByNameArch(patterns=[req])
            for pkg in pkgs:
                algo, checksum, _ = pkg.returnChecksums()[0]
                log_debug("  %s: %s (%s: %s)" % (req, pkg, algo, checksum))
                pkg_hash.update(checksum)

                yumbase.downloadHeader(pkg)
                hdr = pkg.returnLocalHeader()
                log_debug("  File hashes (%s):" %
                    RFC4880_HASHES[hdr.filedigestalgo])
                for name, digest in zip(hdr.filenames, hdr.filedigests):
                    log_debug("    %s: %s" % (name, digest))
                    pkg_hash.update(digest)

        except yum.Errors.PackageSackError as pse:
            log_debug("  %s" % pse)

    log_debug("Package hash: %s" % pkg_hash.hexdigest())
    return pkg_hash.hexdigest()


def build_package(configdir, root, passthrough_args):
    """
    Spawn a mock process to build the package.   Some arguments
    are intercepted and rewritten, for instance --resultdir.
    """
    working_directory = tempfile.mkdtemp()
    log_debug("Mock working directory: %s" % working_directory)

    cmd = ["mock", "--configdir=%s" % configdir,
           "--root=%s" % root,
           "--resultdir=%s" % working_directory] + passthrough_args

    subprocess.call(cmd)
    return working_directory


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    config = os.path.join(intercepted_args.configdir,
                          intercepted_args.root + ".cfg")

    yum_config = load_mock_config(config)
    yumbase = get_yum(yum_config)
    srpm = load_srpm_from_file(passthrough_args[-1])
    pkg_hash = get_srpm_hash(srpm, yumbase)

    cache_basedir = os.path.expanduser(
        os.getenv("PLANEX_CACHEDIR", 
            default=os.path.join("~", ".planex-cache")))

    # Rebuild if not available in the cache
    if not in_cache(cache_basedir, pkg_hash):
        log_debug("Cache miss - rebuilding")
        build_output = build_package(intercepted_args.configdir,
                                     intercepted_args.root, passthrough_args)
        add_to_cache(cache_basedir, pkg_hash, build_output)

    get_from_cache(cache_basedir, pkg_hash, intercepted_args.resultdir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
