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
from planex.globals import (BUILD_ROOT_DIR, SPECS_DIR, SOURCES_DIR, SRPMS_DIR,
                            SPECS_GLOB)
import planex.spec

GITHUB_MIRROR = "~/github_mirror"
MYREPOS = "~/devel2"

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
    base_url = base_url.split('#')[0]
    return "%s#%s/%%{name}-%%{version}.tar.gz" % (base_url, version)


def parse_extended_git_url(url):
    """
    Parse one of our custom rewritten git URLs of the form:
       git:///repos/project#version/archive.tar.gz

    Returns the scheme, host, path, version and archive name
    """
    print "url=%s" % url
    (scheme, host, path, _, _, fragment) = urlparse.urlparse(url)
    assert scheme == "git"

    print "path=%s" % path
    version, archive = None, None

    # urlparse only parses fragments from some URLs, mainly http://,
    # https:// and file://.   With a git:// URL, we have to do it
    # ourselves
    if "#" in path:
        path, fragment = path.split("#")

    print "fragment=%s" % fragment
    if fragment and "/" in fragment:
        version, archive = fragment.split("/")
    else:
        version = fragment

    return(scheme, host, path, version, archive)


def locate_repo(path, myrepos=MYREPOS, github_mirror=GITHUB_MIRROR):
    """
    Returns the location of the repository
    """
    if path.endswith(".git"):
        path = path[:-4]

    if len(path) == 0:
        print "Zero length path!"
        exit(1)

    basename = path.split("/")[-1]

    trials = [
        os.path.expanduser("%s/%s" % (myrepos, basename)),
        os.path.expanduser("%s/%s.git" % (myrepos, basename)),
        "/repos/%s" % basename,
        os.path.expanduser("%s/%s.git" % (github_mirror, path))]

    for trial in trials:
	print "trying " + trial
        if os.path.exists(trial):
            return trial

    return None

def latest_git_tag(url, myrepos=MYREPOS, github_mirror=GITHUB_MIRROR):
    """
    Returns numeric version tag closest to HEAD in the repository.
    """
    # We expect path to be a full git url pointing at a path on the local host
    # We only need the path
    (scheme, _, path, committish, _) = parse_extended_git_url(url)
    assert scheme == "git"

    repo_location = locate_repo(path, myrepos, github_mirror)

    print "Located git repo at: %s" % repo_location

    if(os.path.exists("%s/.git" % repo_location)):
        dotgitdir = "%s/.git" % repo_location
    else:
        dotgitdir = repo_location

    # Hack hack. if the repo name starts with /repos then it's an XS build
    # system one. In that case, the committish isn't going to work (we
    # explicitly only ever build from master, which is synced from a
    # possibly different github branch).
    if dotgitdir.startswith("/repos"):
        committish = None

    cmd = ["git", "--git-dir=%s" % dotgitdir,
         "describe", "--tags"]
    if committish:
        cmd.append(committish)

    description = subprocess.Popen(cmd,
        stdout=subprocess.PIPE).communicate()[0].strip()
    match = re.search("[^0-9]*", description)
    matchlen = len(match.group())
    return description[matchlen:].replace('-', '+')


def fetch_git_source(url, myrepos=MYREPOS, github_mirror=GITHUB_MIRROR, 
                     sources_dir=SOURCES_DIR):
    """
    Fetches an archive of HEAD of the git repository at path.
    Produces a tarball called 'archive_name' in SOURCES_DIR,
    which when unpacked will produce a directory called
    "reponame-version".   This is similar to GitHub's archive
    URLs.
    """

    # We expect path to be a custom git url pointing at a path on
    # the local host.   We only need the path, version and archive_name
    print "url=%s" % url
    (_, _, path, version, archive_name) = parse_extended_git_url(url)
    basename = path.split("/")[-1]

    repo_location = locate_repo(path, myrepos, github_mirror)

    if(os.path.exists("%s/.git" % repo_location)):
        dotgitdir = "%s/.git" % repo_location
    else:
        dotgitdir = repo_location

    for sourcefile in os.listdir(sources_dir):
        if re.search(r'^(%s\.tar)(\.gz)?$' % basename, sourcefile):
            os.remove(sourcefile)
    call(["git", "--git-dir=%s" % dotgitdir, "archive",
          "--prefix=%s-%s/" % (basename, version), "HEAD", "-o",
          "%s/%s" % (sources_dir, archive_name)])


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
    spec = planex.spec.Spec(spec_path)
    return spec.source_urls()


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
    if sources == []:
        print "Failed to get sources for %s" % spec_path
        sys.exit(1)

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
            number_fetched += 1

    return number_fetched, number_skipped


def build_srpm(spec_path):
    """
    Builds an SRPM from the spec file at spec_path.

    Assumes that all source files have already been downloaded to
    the rpmbuild sources directory, and are correctly named.
    """
    call(["rpmbuild", "-bs", spec_path,
          "--nodeps", "--define", "_topdir %s" % BUILD_ROOT_DIR])


def main(argv):
    """
    Main function.  Process all the specfiles in the directory
    given by config_dir.
    """
    config_dir, use_distfiles = parse_cmdline(argv)

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


def usage(name):
    """
    Print usage string
    """
    print "%s --config-dir=<config-dir>" % name


def parse_cmdline(argv):
    """
    Parse command line options
    """
    config_dir = None
    use_distfiles = False
    try:
        longopts = ["config-dir=", "use-distfiles"]
        opts, _ = getopt.getopt(argv[1:], "", longopts)
    except getopt.GetoptError, err:
        print str(err)
        usage(argv[0])
        sys.exit(1)
    for opt, arg in opts:
        if opt == "--config-dir":
            config_dir = arg
        if opt == "--use-distfiles":
            use_distfiles = True
    if config_dir == None:
        usage(argv[0])
        sys.exit(1)
    return (config_dir, use_distfiles)


def _main():
    """Entry point for setuptools CLI wrapper"""
    main(sys.argv)


if __name__ == "__main__":
    _main()
