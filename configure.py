#!/usr/bin/env python

"""
Builds SRPMs for the tarballs or Git repositories in <component-specs-dir>.
"""

import getopt
import sys
import os.path
from subprocess import call
import urlparse
import subprocess
import re
import glob
import shutil
from planex_globals import (BUILD_ROOT_DIR, SPECS_DIR, SOURCES_DIR, SRPMS_DIR,
                            SPECS_GLOB)

# HACK: Monkey-patch urlparse to understand git:// URLs
# This is not needed for more modern Pythons
#    http://bugs.python.org/issue7904
urlparse.uses_netloc.append('git')


def rewrite_to_distfiles(url):
    """
    Rewrites url to refer to the local distfiles cache.
    """
    basename = url.split("/")[-1]
    return "file:///distfiles/ocaml2/" + basename

def fetch_url(url, rewrite=None):
    """
    Fetches a url, rewriting it using 'rewrite' if it exists

    Only fetches if the target file doesn't already exist.

    Returns 1 if it actually fetched something, otherwise 0.
    """
    if rewrite:
        url = rewrite(url)
    basename = url.split("/")[-1]
    final_path = os.path.join(SOURCES_DIR, basename)
    if os.path.exists(final_path):
        return 0
    else:
        if call(["curl", "-k", "-L", "-o", final_path, url]) != 0:
            print "Error downloading '%s'" % url
            sys.exit(1)
        return 1


def make_extended_git_url(base_url, version):
    """
    Generate a custom git repository URL of the form:
       <base_url>#<version>/%{name}-%{version}.tar.gz

    Given such a URL, fetch_git_source() will generate a tarball
    of the repository with the same form as a tarball downloaded
    from a GitHub archive URL.
    """
    return "%s#%s/%%{name}-%%{version}.tar.gz" % (base_url, version)


def parse_extended_git_url(url):
    """
    Parse one of our custom rewritten git URLs of the form:
       git:///repos/project#version/archive.tar.gz

    Returns the scheme, host, path, version and archive name
    """
    (scheme, host, path, _, _, _) = urlparse.urlparse(url)
    assert scheme == "git"
    assert host == ""

    fragment, version, archive = None, None, None

    # urlparse only parses fragments from some URLs, mainly http://,
    # https:// and file://.   With a git:// URL, we have to do it
    # ourselves
    if "#" in path:
        path, fragment = path.split("#")

    if fragment and "/" in fragment:
        version, archive = fragment.split("/")

    return(scheme, host, path, version, archive)


def latest_git_tag(url):
    """
    Returns numeric version tag closest to HEAD in the repository.
    """
    # We expect path to be a full git url pointing at a path on the local host
    # We only need the path
    (scheme, host, path, _, _) = parse_extended_git_url(url)
    assert scheme == "git"
    assert host == ""

    description = subprocess.Popen(
        ["git", "--git-dir=%s/.git" % path,
         "describe", "--tags"],
        stdout=subprocess.PIPE).communicate()[0].strip()
    match = re.search("[^0-9]*", description)
    matchlen = len(match.group())
    return description[matchlen:].replace('-', '+')


def fetch_git_source(url):
    """
    Fetches an archive of HEAD of the git repository at path.
    Produces a tarball called 'archive_name' in SOURCES_DIR,
    which when unpacked will produce a directory called
    "reponame-version".   This is similar to GitHub's archive
    URLs.
    """

    # We expect path to be a custom git url pointing at a path on
    # the local host.   We only need the path, version and archive_name
    (_, _, path, version, archive_name) = parse_extended_git_url(url)
    basename = path.split("/")[-1]

    for sourcefile in os.listdir(SOURCES_DIR):
        if re.search(r'^(%s\.tar)(\.gz)?$' % basename, sourcefile):
            os.remove(sourcefile)
    call(["git", "--git-dir=%s/.git" % path, "archive",
          "--prefix=%s-%s/" % (basename, version), "HEAD", "-o",
          "%s/%s" % (SOURCES_DIR, archive_name)])


def name_from_spec(spec_path):
    """
    Returns the base name of the packages defined in the spec file at spec_path.
    Ideally we would do this using the Python RPM library, but the version in
    CentOS 5 doesn't expose it.
    """
    spec = open(spec_path)
    lines = spec.readlines()
    spec.close()

    name = [l.strip() for l in lines
            if l.strip().lower().startswith('name:')][0].split(':')[1].strip()
    return name


def check_spec_name(spec_path):
    """
    The spec file name should match the base name of the packages it produces.
    Exit with an error if this is not the case.
    """
    pkg_name = name_from_spec(spec_path)
    if re.sub(r".spec(.in)?$", "", os.path.basename(spec_path)) != pkg_name:
        sys.stderr.write( "error: spec file name '%s' "
                          "does not match package name '%s'\n" %
                          (spec_path, pkg_name))
        sys.exit(1)


def sources_from_spec(spec_path):
    """
    Extracts all source URLS from the spec file at spec_path.

    Returns a list of source URLs with RPM macros expanded.
    """
    sources = []
    p1 = subprocess.Popen(
        ['perl', '-pe', 's/^\\s*Version\\s*:\\s*\\@VERSION\\@.*/Version: 123.planex789\\n/i', spec_path],
         stdout=subprocess.PIPE)
    p2 = subprocess.Popen(
        ["spectool", "--list-files", "--sources", '<&STDIN'],
         stdout=subprocess.PIPE,stdin=p1.stdout)
    p1.stdout.close()
    lines = p2.communicate()[0].strip().split("\n")
    p1.wait()
    if p2.returncode != 0 or p1.returncode != 0:
        sys.stderr.write("error parsing spec file '%s'\n" % spec_path)
        sys.exit(1)
    for line in lines:
        match = re.match(r"^([Ss]ource\d*):\s+(\S+)$", line)
        if match:
            sources.append(match.group(2))
    return sources


def preprocess_spec(spec_in_path, spec_out_path, version, tarball_name):
    """
    Preprocesses a spec file containing placeholders.
    Writes the result to the same filename, with the '.in' extension
    stripped, in spec_out_path.
    """
    assert spec_in_path.endswith('.in')

    spec_in = open(spec_in_path)
    spec_contents = spec_in.readlines()
    spec_in.close()

    output_filename = os.path.basename(spec_in_path)[:-len(".in")]
    spec_out = open(os.path.join(spec_out_path, output_filename), "w")

    for line in spec_contents:
        match = re.match(r'^([Ss]ource0:\s+)(.+)\n', line)
        if match:
            line = match.group(1) + tarball_name + "\n"

        match = re.match(r'^([Vv]ersion:\s+)(.+)\n', line)
        if match:
            line = match.group(1) + version + "\n"

        spec_out.write(line)

    spec_out.close()


def prepare_srpm(spec_path, use_distfiles):
    """
    Downloads sources needed to build an SRPM from the spec file
    at spec_path.   Pre-processes the spec file, if needed.
    """
    # check the .spec file exists, or .spec.in if we're processing the spec
    if not(os.path.exists(spec_path)):
        print "%s doesn't exist" % spec_path
        sys.exit(1)

    # Pull out the source list.   If the spec file pulls its sources
    # from a Git repository, we need to prepreprocess the spec file
    # to fill in the latest version tag from the repository.
    sources = sources_from_spec(spec_path)
    assert sources

    number_skipped = 0
    number_fetched = 0

    for source in sources:
        (scheme, _, _, _, _, _) = urlparse.urlparse(source)

        if scheme in ['file', 'http', 'https']:
            rewrite_fn = None
            if use_distfiles:
                rewrite_fn = rewrite_to_distfiles
            result = fetch_url(source, rewrite_fn)
            number_fetched += result
            number_skipped += (1 - result)

        if scheme in ['git']:
            fetch_git_source(source)

    return number_fetched, number_skipped


def build_srpm(spec_path):
    """
    Builds an SRPM from the spec file at spec_path.

    Assumes that all source files have already been downloaded to
    the rpmbuild sources directory, and are correctly named.
    """
    call(["rpmbuild", "-bs", spec_path, 
          "--nodeps", "--define", "_topdir %s" % BUILD_ROOT_DIR])


def main(config_dir, use_distfiles):
    """
    Main function.  Process all the specfiles in the directory
    given by config_dir.
    """

    for path in [SRPMS_DIR, SPECS_DIR]:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

    if not os.path.exists(SOURCES_DIR):
        os.makedirs(SOURCES_DIR)

    # Pull in any required patches
    patches_dir = os.path.join(config_dir, 'SOURCES')
    for patch in glob.glob(os.path.join(patches_dir, '*')):
        shutil.copy(patch, SOURCES_DIR)

    # Pull in spec files, preprocessing if necessary
    for spec_path in glob.glob(os.path.join(config_dir, "*.spec*")):
        check_spec_name(spec_path)
        if spec_path.endswith('.in'):
            print "Configuring package with spec file: %s" % spec_path
            sources = sources_from_spec(spec_path)
            version = latest_git_tag(sources[0])
            repo_url = make_extended_git_url(sources[0], version)
            preprocess_spec(spec_path, SPECS_DIR, version, repo_url)
        else:
            shutil.copy(spec_path, SPECS_DIR)

    number_fetched = 0
    number_skipped = 0

    # Build SRPMs
    for spec_path in glob.glob(SPECS_GLOB):
        fetched, skipped = prepare_srpm(spec_path, use_distfiles)
        number_fetched += fetched
        number_skipped += skipped
        build_srpm(spec_path)

    print "number of packages skipped: %d" % number_skipped
    print "number of packages fetched: %d" % number_fetched

def usage():
    print "%s --config-dir=<config-dir>" % __file__

if __name__ == "__main__":
    config_dir = None
    use_distfiles = False
    try:
        longopts = ["config-dir=", "use-distfiles"]
        opts, _ = getopt.getopt(sys.argv[1:], "", longopts)
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(1)
    for o, a in opts:
        if o == "--config-dir":
            config_dir = a
        if o == "--use-distfiles":
            use_distfiles = True
    if config_dir == None:
        usage()
        sys.exit(1)
    main(config_dir, use_distfiles)
