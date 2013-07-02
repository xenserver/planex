#!/usr/bin/env python

import sys
import os.path
from string import maketrans
from subprocess import call
import demjson
import urlparse
import subprocess
import re
import glob
import shutil

CONFIG = "./conf.json"
SOURCESDIR = "./SOURCES"
SRPMSDIR = "./SRPMS"

number_skipped = 0
number_fetched = 0


def parse_config(conf_dir):
    """Returns _list_ of dictionaries of the following form:
        {
          'spec': <spec_filename>,
          'sources': [{'url': <url>, 'override': <name-override>}]
        }
    """
    f = open(os.path.join(conf_dir, CONFIG), "r")
    json = f.read()
    f.close()
    return demjson.decode(json)

def fetch_url(url,override):
    """ Fetch a url, renaming it to 'override' if it exists.

    Only fetches if it doesn't already exist.

    Returns 1 if it actually fetched something.
    """
    final_name = url.split("/")[-1]
    if override is not None:
        final_name = override
    final_path = os.path.join(SOURCESDIR, final_name)
    if os.path.exists(final_path):
        return 0
    else:
        print "fetching %s -> %s" % (url, final_path)
        if call(["curl", "-k", "-L", "-o", final_path, url]) != 0:
            print "Error downloading '%s'" % url
            sys.exit(1)
        return 1

def fetch_git_source(path):
    """ Fetches an archive of a git repository.

    Returns a version string, the tarball's prefix, and the pathname of the tarball.
    """
    description=subprocess.Popen(["git", "--git-dir=%s/.git" % path, "describe", "--tags"], stdout=subprocess.PIPE).communicate()[0].strip()
    p = re.compile("[^0-9]*")
    m = p.search(description)
    l = len(m.group())
    version = description[l:].translate(maketrans('-','+'))
    final_name = path.split("/")[-1]
    prefix = final_name
    call(["rm", "-f", "%s/%s.tar" % (SOURCESDIR,final_name)])
    call(["rm", "-f", "%s/%s.tar.gz" % (SOURCESDIR,final_name)])
    call(["git","--git-dir=%s/.git" % path, "archive","--prefix=%s/" % prefix, "--format=tar", "HEAD", "-o", "%s/%s.tar" % (SOURCESDIR,final_name)])
    call(["gzip","%s/%s.tar" % (SOURCESDIR,final_name)])    
    return (version,prefix,"%s.tar.gz" % final_name)

def prepare_srpm(pkg):
    global number_skipped, number_fetched

    spec = os.path.join(conf_dir, pkg['spec'])
    sources = pkg['sources']
    process_spec = False

    # If the config file mentions a git repo, we assume we're building a development
    # RPM, whose spec file needs preprocessing (process_spec=True).
    for source in sources:
        scheme=urlparse.urlparse(source['url'])[0]
        if scheme=='git':
            process_spec = True
            if len(sources) > 1:
                print "Can't cope with more than one source for a git type package"
                sys.exit(1)

    spec_path = spec
    if process_spec:
        spec_path = "%s.in" % spec

    # check the .spec file exists, or .spec.in if we're processing the spec
    if not(os.path.exists(spec_path)):
        print "%s doesn't exist" % spec_path
        sys.exit(1)

    for source in sources:
        (scheme,netloc,path,params,query,fragment) = urlparse.urlparse(source['url'])

        if (scheme=='file' or scheme=='http' or scheme=='https'):
            url, override = source['url'], source['override']
            result = fetch_url(url,override)
            number_fetched += result
            number_skipped += (1 - result)
        if scheme=='git':
            print "Configuring package with spec file: %s" % spec
            (version,prefix,source_tarball) = fetch_git_source(path)
            spec_contents=subprocess.Popen(["sed","-e","s/@VERSION@/%s/g" % version,
                                            "-e","s/@PREFIX@/%s/g" % prefix, 
                                            "-e","s/@SOURCE@/%s/g" % source_tarball,
                                            "%s" % spec_path],stdout=subprocess.PIPE).communicate()[0]
            f = open(spec,"w")
            f.write(spec_contents)
            f.close()

def build_srpm(pkg):
    call(["rpmbuild", "-bs", "%s/%s" % (conf_dir, pkg['spec']), "--nodeps", "--define", "_topdir ."])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage:"
        sys.exit(1)
    conf_dir = sys.argv[1];

    for dir in [SOURCESDIR, SRPMSDIR]:
        if not os.path.exists(dir):
            os.makedirs(dir)	

    # pull in any required patches
    sources_dir = os.path.join(conf_dir, 'SOURCES')
    if os.path.exists(sources_dir):
        for patch in glob.glob(os.path.join(sources_dir, '*')):
            shutil.copy(patch, SOURCESDIR)

    config = parse_config(conf_dir)

    for pkg in config:
        prepare_srpm(pkg)
        build_srpm(pkg)

    print "number of packages skipped: %d" % number_skipped
    print "number of packages fetched: %d" % number_fetched

