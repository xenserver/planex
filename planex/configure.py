#!/usr/bin/env python

"""
Builds SRPMs for the tarballs or Git repositories in <component-specs-dir>.
"""

import argparse
import sys
import os.path
import urlparse
import re
import glob
import shutil
from planex.globals import (BUILD_ROOT_DIR, SPECS_DIR, SOURCES_DIR, SRPMS_DIR,
                            SPECS_GLOB, HASHFN)
import planex.spec
from planex.util import (bcolours, print_col, run, dump_cmds, rewrite_url)
from planex import sources

GITHUB_MIRROR = "~/github_mirror"

manifest = {}

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


def preprocess_spec(spec_in_path, spec_out_path, scmsources, source_mapping):
    """
    Preprocesses a spec file containing placeholders.
    Writes the result to the same filename, with the '.in' extension
    stripped, in spec_out_path.
    """
    assert spec_in_path.endswith('.in')

#    print "preprocess_spec: mapping=%s" % source_mapping
    spec_in = open(spec_in_path)
    spec_contents = spec_in.readlines()
    spec_in.close()

    output_filename = os.path.basename(spec_in_path)[:-len(".in")]
    spec_out = open(os.path.join(spec_out_path, output_filename), "w")

    spec_basename = spec_in_path.split("/")[-1]

    subs = {}

    for (index,source) in enumerate(scmsources):
        subs['source%d_version' % index] = source.version
        subs['source%d_hash' % index] = source.scmhash

    subs.update({
	"version" : "+".join([source.version for source in scmsources]),
        "release" : "1%{?extrarelease}" })

    for line in spec_contents:
        match = re.match(r'^([Ss]ource\d*:\s+)(.+)\n', line)
# TODO: strip whitespace from match.group(2)
        if match and match.group(2) in source_mapping:
#            print "Got a source mapping"
            line = match.group(1) + source_mapping[match.group(2)] + "\n"
            print "  " + spec_basename + ": mapping %s to %s" % (match.group(2), 
                                        source_mapping[match.group(2)])

        match = re.match(r'^(%define planex_)([^\s]+)(.+)\n', line)
        if match:
            line = match.group(1) + match.group(2) + " " + subs[match.group(2)] + "\n"

        spec_out.write(line)

    spec_out.close()


def prepare_srpm(spec_path, config):
    """
    Downloads sources needed to build an SRPM from the spec file
    at spec_path.
    """
    # check the .spec file exists, or .spec.in if we're processing the spec
    if not(os.path.exists(spec_path)):
        print "%s doesn't exist" % spec_path
        sys.exit(1)

    # Pull out the source list.   If the spec file pulls its sources
    # from a Git repository, we need to prepreprocess the spec file
    # to fill in the latest version tag from the repository.
    allsources = sources_from_spec(spec_path)
    if allsources == []:
        print "Failed to get sources for %s" % spec_path
        sys.exit(1)

    allsources = [rewrite_url(url, config.mirror_path) for url in allsources]
    for source in allsources:
        sources.Source(source, config).archive()

def get_hashes(ty):
    spec_files = glob.glob(os.path.join(SPECS_DIR,"*"))
    sources_files = glob.glob(os.path.join(SOURCES_DIR,"*"))
    all_files = spec_files + sources_files
    if ty=="md5":
        cmd = ["md5sum"] + all_files
    elif ty=="sha256":
        cmd = ["sha256sum"] + all_files
    else:
        print "Invalid hash type"
        raise Exception
    result = run(cmd)['stdout'].strip().split('\n')
    def fix(x):
        words = x.split()
        if len(words) == 2:
            fname = words[1].split("/")[-1]
            return (fname,words[0])
        else:
            return None
    fixed = [fix(x) for x in result]
    return dict(fixed)       

def ensure_existing_ok(hashes, spec_path):
    pkg_name = name_from_spec(spec_path)

    one_correct = False

    for srpm in glob.glob(os.path.join(SRPMS_DIR, '%s-*.src.rpm' % pkg_name)):
        # Check it's for the right package:
        cmd = ["rpm","-qp",srpm, "--qf", "%{name}"]
        result = run(cmd)['stdout'].strip().split('\n')
        
        if result[0] == pkg_name:
            cmd = ["rpm","--dump","-qp",srpm]
            result = run(cmd)['stdout'].strip().split('\n')
            ok = True
            for line in result:
                split = line.split()
                fname = split[0]
                thishash=split[3]
                if fname not in hashes or hashes[fname] != thishash:
                    ok = False

            if not ok:
                print_col(bcolours.WARNING,"WARNING: Removing SRPM '%s' (hash mismatch with desired)" % srpm)
                os.remove(srpm)
            else:
                one_correct = True

    return one_correct

def build_srpm(hashes, spec_path):
    """
    Builds an SRPM from the spec file at spec_path.

    Assumes that all source files have already been downloaded to
    the rpmbuild sources directory, and are correctly named.
    """
    is_ok = ensure_existing_ok(hashes, spec_path)

    if not is_ok:
        cmd = (["rpmbuild", "-bs", spec_path,
                "--nodeps", "--define", "_topdir %s" % BUILD_ROOT_DIR])
        run(cmd)
        return 1
    else:
        return 0

def prepare_buildroot():
    """Create a clean rpmbuild directory structure"""

    if os.path.exists(SPECS_DIR):
        shutil.rmtree(SPECS_DIR)
    os.makedirs(SPECS_DIR)

    for path in [SRPMS_DIR, SOURCES_DIR]:
        if not os.path.exists(path):
            os.makedirs(path)

def copy_patches_to_buildroot(config):
    """Copy patches into the build root"""
    patches_dir = os.path.join(config.config_dir, config.sources_path)
    for patch in glob.glob(os.path.join(patches_dir, '*')):
        shutil.copy(patch, SOURCES_DIR)

def is_scm(uri):
   if uri.startswith("git://"):
	return True
   if uri.startswith("hg://"):
	return True
   return False

def copy_specs_to_buildroot(config):
    """Pull in spec files, preprocessing if necessary"""
    config_dir = config.config_dir
    specs = glob.glob(os.path.join(config_dir, config.specs_path, "*.spec"))
    spec_ins = glob.glob(os.path.join(config_dir, config.specs_path, "*.spec.in"))
    for spec_path in specs + spec_ins:
        check_spec_name(spec_path)
        basename = spec_path.split("/")[-1]
        if spec_path.endswith('.in'):
            print_col(bcolours.OKGREEN,"Configuring and fetching sources for '%s'" % basename)
            scmsources = [sources.Source(source, config) for source in sources_from_spec(spec_path)
                          if (is_scm(source))]
            mapping = {}
            for source in scmsources:
                source.pin()
                manifest[source.repo_name]=source.scmhash
                mapping[source.orig_url]=source.extendedurl
            preprocess_spec(spec_path, SPECS_DIR, scmsources, mapping)
        else:
            print_col(bcolours.OKGREEN, "Fetching sources for '%s'" % basename)
            shutil.copy(spec_path, SPECS_DIR)

def build_srpms(config):
    """Build SRPMs for all SPECs"""
    print_col(bcolours.OKGREEN, "Building/checking SRPMS for all files in SPECSDIR")
    print "  Getting %s hashes for source to check against existing SRPMS..." % HASHFN,
    sys.stdout.flush()
    hashes = get_hashes(HASHFN)
    print "OK"
    specs = glob.glob(SPECS_GLOB)
    n=0
    for spec_path in specs:
        prepare_srpm(spec_path, config)
        n+=build_srpm(hashes, spec_path)
    print_col(bcolours.OKGREEN,"Rebuilt %d out of %d SRPMS" % (n,len(specs)))

def dump_manifest():
    print "---------------------------------------"
    print_col(bcolours.OKGREEN,"MANIFEST")
    sources = manifest.keys()
    sources.sort()
    for source in sources:
        basename = source.split("/")[-1]
        if basename.endswith(".git"):
            basename = basename[:-4]
        if basename.endswith(".hg"):
            basename = basename[:-3]
        print basename.rjust(40), manifest[source]

def sort_mockconfig(config):
    config_dir = config.config_dir
    if not os.path.exists('mock'):
        os.makedirs('mock')
        print_col(bcolours.OKGREEN, "Creating mock configuration for current working directory")
        # Copy in all the files from config_dir
        mock_files = glob.glob(os.path.join(config_dir,'mock','*'))

        for f in mock_files:
            basename = f.split('/')[-1]
            dest_fname = os.path.join('mock',basename)
            print "  copying file '%s' to '%s'" % (f,dest_fname)
            shutil.copyfile(f,dest_fname)
            planex_build_root = os.path.join(os.getcwd(),BUILD_ROOT_DIR)
            with open(dest_fname,'w') as dst:
                with open(f) as src:
                    for line in src:
                        dst.write(re.sub(r"@PLANEX_BUILD_ROOT@", planex_build_root, line))

def main(argv):
    """
    Main function.  Process all the specfiles in the directory
    given by config_dir.
    """
    config = parse_cmdline()
    prepare_buildroot()
    sort_mockconfig(config)
    copy_patches_to_buildroot(config)
    copy_specs_to_buildroot(config)
    build_srpms(config)
    dump_manifest()

def parse_cmdline(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Configure the planex build directory.

    This command will generate the directory structure planex requires
    to build RPMs. The following directories will be created in the
    curent directory:

        planex-build-root/{RPMS,SRPMS,SPECS}
        mock

    The configuration directory should contain a template mock
    configuration directory, a set of SPEC files and/or SPEC file
    templates. The files in the mock template will be processed and
    the following substitions made:

        @PLANEX_BUILD_ROOT@ -> the full path of the planex-build-root 
                               directory.

    The SPEC file templates (.spec.in) are processed in the following way.
    Any Source directive that references a git or mercurial repository will
    be extended with a SCM hash and an archive filename. The filename contains
    a version derived from the SCM repository. Additionally, the following
    definitions are also rewritten if they were present in the template:

        %source{n}_version -> version derived from the nth repository
        %source{n}_hash    -> SCM hash from the nth repository
        %planex_version    -> combined version
        %planex_release    -> 1%{?extrarelease}
    """,formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        '--mirror_path', help='Rewrite URLs to point to this directory', 
        default="")
    parser.add_argument(
        '--repos_mirror_path', help='Path to a local repository mirror directory. '
        'This should be a file path where for a git url '
        '"git://host.com/some/path.git" the mirror '
        'should contain <mirror_path>/host.com/some/path.git', 
        default="")
    parser.add_argument(
        '--repos_path', help='Local path to the repositories',
        default="repos")
    parser.add_argument(
        '--sources_path', help='Path (relative to config_dir) to the SOURCES directory containing patches '
        'and extra sources for the RPMs',
        default="SOURCES")
    parser.add_argument(
        '--specs_path', help='Path (relative to config_dir) to the SPECS directory containing spec '
        'files to be preprocessed as well as those simply to be built.',
        default="SPECS")
    parser.add_argument('config_dir', help='Configuration directory')
    return parser.parse_args(argv)


def _main():
    """Entry point for setuptools CLI wrapper"""
    main(sys.argv)


if __name__ == "__main__":
    _main()
