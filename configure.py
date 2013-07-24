#!/usr/bin/env python

import sys
import os.path
from subprocess import call
import urlparse
import subprocess
import re
import glob
import shutil

SOURCESDIR = "./SOURCES"
SRPMSDIR = "./SRPMS"

number_skipped = 0
number_fetched = 0

def rewrite_to_distfiles(url):
    """
    Rewrites url to refer to the local distfiles cache.
    """
    basename = url.split("/")[-1]
    return "file:///distfiles/ocaml/" + basename
    

def fetch_url(url, rewrite=None):
    """ 
    Fetches a url, rewriting it using 'rewrite' if it exists

    Only fetches if the target file doesn't already exist.

    Returns 1 if it actually fetched something, otherwise 0.
    """
    if rewrite:
        url = rewrite(url)
    basename = url.split("/")[-1]
    final_path = os.path.join(SOURCESDIR, basename)
    if os.path.exists(final_path):
        return 0
    else:
        if call(["curl", "-k", "-L", "-o", final_path, url]) != 0:
            print "Error downloading '%s'" % url
            sys.exit(1)
        return 1

def latest_git_tag(path):
    """
    Returns numeric version tag closest to HEAD in the repository.
    """
    # strip the git:// url scheme
    path = re.sub( "^git://", "", path )

    description = subprocess.Popen(
        ["git", "--git-dir=%s/.git" % path,
         "describe", "--tags"],
        stdout=subprocess.PIPE).communicate()[0].strip()
    m = re.search("[^0-9]*", description)
    l = len(m.group())
    return description[l:].replace('-', '+')


def fetch_git_source(path):
    """
    Fetches an archive of a git repository.

    Returns a version string, the tarball's prefix, and the pathname of
    the tarball.
    """
    # strip the git:// url scheme
    path = re.sub( "^git://", "", path )
    version = latest_git_tag(path)
    final_name = path.split("/")[-1]
    [os.remove(f)
        for f in os.listdir('SOURCES')
        if re.search('^(%s\.tar)(\.gz)?$' % final_name, f)]
    prefix = final_name
    call(["git", "--git-dir=%s/.git" % path, "archive",
          "--prefix=%s/" % prefix, "--format=tar", "HEAD", "-o",
          "%s/%s.tar" % (SOURCESDIR, final_name)])
    call(["gzip", "%s/%s.tar" % (SOURCESDIR, final_name)])
    return (version, prefix, "%s.tar.gz" % final_name)


def sources_from_spec(spec_path):
    """
    Extracts all source URLS from the spec file at spec_path.

    Returns a list of source URLs with RPM macros expanded.
    """
    sources = []
    lines = subprocess.Popen(
        ["./spectool", "--list-files", "--sources", spec_path],
         stdout=subprocess.PIPE).communicate()[0].strip().split("\n")
    for l in lines:
        m = re.match("^([Ss]ource\d*):\s+(\S+)$", l)
	assert m
        sources.append(m.groups()[1])
    return sources 


def prepare_srpm(spec_path):
    """
    Downloads sources needed to build an SRPM from the spec file
    at spec_path.   Pre-processes the spec file, if needed.
    """
    global number_skipped, number_fetched

    # check the .spec file exists, or .spec.in if we're processing the spec
    if not(os.path.exists(spec_path)):
        print "%s doesn't exist" % spec_path
        sys.exit(1)

    # Pull out the source list.   If the spec file pulls its sources 
    # from a Git repository, we need to prepreprocess the spec file 
    # to fill in the latest version tag from the repository.
    sources = sources_from_spec(spec_path)
    assert sources

    if spec_path.endswith('.in'):
        print "Configuring package with spec file: %s" % spec_path
        version, prefix, filename = fetch_git_source(sources[0])
        # Rewrite the @VERSION@ and @PREFIX@ placeholders in the spec
        # and add .tar.gz to the source URL, so rpmbuild finds the file.
        spec_contents = subprocess.Popen(
            ["sed", "-e", "s/@VERSION@/%s/g" % version, 
             "-e", "s/@PREFIX@/%s/g" % prefix, 
             "-e", "s$%s$%s.tar.gz$g" % (sources[0], sources[0]),
             "%s" % spec_path],
            stdout=subprocess.PIPE).communicate()[0]
        f = open(os.path.splitext(spec_path)[0], "w")
        f.write(spec_contents)
        f.close()
        spec_path = os.path.splitext(spec_path)[0]
        return

    for source in sources:
        (scheme, _, path, _, _, _) = urlparse.urlparse(
            source)

        if scheme in ['file', 'http', 'https']:
            result = fetch_url(source, rewrite_to_distfiles)
            number_fetched += result
            number_skipped += (1 - result)


def build_srpm(spec_path):
    """
    Builds an SRPM from the spec file at spec_path.

    Assumes that all source files have already been downloaded to 
    the rpmbuild sources directory, and are correctly named. 
    """
    call(["rpmbuild", "-bs", spec_path, 
          "--nodeps", "--define", "_topdir ."])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: %s <component-specs-dir>" % __file__
        sys.exit(1)
    conf_dir = sys.argv[1]

    for dir in [SOURCESDIR, SRPMSDIR]:
        if os.path.exists(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)

    # pull in any required patches
    sources_dir = os.path.join(conf_dir, 'SOURCES')
    if os.path.exists(sources_dir):
        for patch in glob.glob(os.path.join(sources_dir, '*')):
            shutil.copy(patch, SOURCESDIR)

    for spec_path in glob.glob(os.path.join(conf_dir, "*.spec*")):
        prepare_srpm(spec_path)
        spec_path = re.sub(".in$", "", spec_path) 
        build_srpm(spec_path)

    print "number of packages skipped: %d" % number_skipped
    print "number of packages fetched: %d" % number_fetched
