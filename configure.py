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
SPECSDIR = "./SPECS"

number_skipped = 0
number_fetched = 0

# HACK: Monkey-patch urlparse to understand git:// URLs
# This is not needed for more modern Pythons
#    http://bugs.python.org/issue7904
urlparse.uses_netloc.append('git')

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
    # We expect path to be a full git url pointing at a path on the local host
    # We only need the path
    (scheme, host, path, _, _, _) = urlparse.urlparse(path)
    assert scheme == "git"
    assert host == ""

    description = subprocess.Popen(
        ["git", "--git-dir=%s/.git" % path,
         "describe", "--tags"],
        stdout=subprocess.PIPE).communicate()[0].strip()
    m = re.search("[^0-9]*", description)
    l = len(m.group())
    return description[l:].replace('-', '+')


def fetch_git_source(path, version, archive_name):
    """
    Fetches an archive of HEAD of the git repository at path.
    Produces a tarball called 'archive_name' in SOURCESDIR,
    which when unpacked will produce a directory called
    "reponame-version".   This is similar to GitHub's archive
    URLs.
    """

    # We expect path to be a full git url pointing at a path on the local host
    # We only need the path
    (scheme, host, path, _, _, _) = urlparse.urlparse(path)
    assert scheme == "git"
    assert host == ""

    basename = path.split("/")[-1]
    [os.remove(f)
        for f in os.listdir('SOURCES')
        if re.search('^(%s\.tar)(\.gz)?$' % basename, f)]
    call(["git", "--git-dir=%s/.git" % path, "archive",
          "--prefix=%s-%s/" % (basename, version), "HEAD", "-o",
          "%s/%s" % (SOURCESDIR, archive_name)])


def name_from_spec(spec_path):
    """
    Returns the base name of the packages defined in the spec file at spec_path.
    """
    f = open(spec_path)
    lines = f.readlines()
    f.close()

    name = [l.strip() for l in lines 
            if l.strip().lower().startswith('name:')][0].split(':')[1].strip()
    return name 


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


def preprocess_spec(spec_path, version, tarball_name):
    """
    Preprocesses a spec file containing placeholders and
    returns the path to the resulting file.
    """
    spec_in = open(spec_path)
    spec_contents = spec_in.readlines()
    spec_in.close()

    f = open(os.path.splitext(spec_path)[0], "w")
    for line in spec_contents:
        match = re.match( '^([Ss]ource0:\s+)(.+)\n', line )
        if match:
            line = match.group(1) + tarball_name + "\n"

        match = re.match( '^([Vv]ersion:\s+)(.+)\n', line )
        if match:
            line = match.group(1) + version + "\n"

        f.write(line)
    f.close()


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
        version = latest_git_tag(sources[0])
        tarball_name = "%s-%s.tar.gz" % (name_from_spec(spec_path), version)
        fetch_git_source(sources[0], version, tarball_name)
        preprocess_spec(spec_path, version, tarball_name)
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

    for dir in [SOURCESDIR, SRPMSDIR, SPECSDIR]:
        if os.path.exists(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)

    # pull in any required patches
    sources_dir = os.path.join(conf_dir, 'SOURCES')
    if os.path.exists(sources_dir):
        for patch in glob.glob(os.path.join(sources_dir, '*')):
            shutil.copy(patch, SOURCESDIR)

    for spec_path in glob.glob(os.path.join(conf_dir, "*.spec*")):
        shutil.copy(spec_path, SPECSDIR)

    for spec_path in glob.glob(os.path.join(SPECSDIR, "*.spec*")):
        prepare_srpm(spec_path)
        spec_path = re.sub(".in$", "", spec_path) 
        build_srpm(spec_path)

    print "number of packages skipped: %d" % number_skipped
    print "number of packages fetched: %d" % number_fetched
