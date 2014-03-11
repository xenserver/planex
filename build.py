#!/usr/bin/env python

# Build a bunch of SRPMs

import getopt
import sys
import os
import glob
import subprocess
import shutil
import rpm
import hashlib
import platform

from planex_globals import (BUILD_ROOT_DIR, SRPMS_DIR, RPMS_DIR, BUILD_DIR,
                            SPECS_GLOB)


TMP_RPM_PATH = "/tmp/RPMS"
RPM_TOP_DIR = os.path.join(os.getcwd(), BUILD_ROOT_DIR)
CACHE_DIR = "rpmcache"


def doexec(args, inputtext=None):
    """Execute a subprocess, then return its return code, stdout and stderr"""
    print "Executing: %s" % " ".join(args)
    myenv = os.environ.copy()
    myenv['HOME'] = RPM_TOP_DIR
    proc = subprocess.Popen(args, env=myenv, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            close_fds=True)
    (stdout, stderr) = proc.communicate(inputtext)
    ret = proc.returncode
    return (ret, stdout, stderr)


def get_srpm_info(srpm):
    for spec_path in glob.glob(SPECS_GLOB):
        os.unlink(spec_path)
    (ret, _, _) = doexec(["rpm", "-i", srpm])
    assert ret == 0
    myspecfile = glob.glob(SPECS_GLOB)[0]
    spec = rpm.ts().parseSpec(myspecfile)
    info = {}
    info['deps'] = spec.sourceHeader["requires"]
    info['arch'] = return_arch_type()
    info['packages'] = [{'name':p.header['name']} for p in spec.packages]
    info['srcrpm'] = srpm
    content_file = open(myspecfile,'r')
    info['spec'] = content_file.read()
    content_file.close()
    return info

def return_arch_type():
	arch = platform.machine()
	if arch == 'x86_64':
		return 'x86_64'
	else:
		return 'i686'


def extract_target(srpm_infos, srpm_filename):
    """
    Given a list of srpm_info and an srpm filename, return the target arch
    """
    for srpm_info in srpm_infos:
        if srpm_info["srcrpm"] == srpm_filename:
            return srpm_info["arch"]


def get_package_to_srpm_map(srpm_info):
    pkg_map = {}
    for srpm in srpm_info:
        for package in srpm['packages']:
            pkg_map[package['name']] = srpm['srcrpm']
    return pkg_map


def get_deps(srpm_infos):
    p_to_s_map = get_package_to_srpm_map(srpm_infos)
    deps = {}
    for srpm_info in srpm_infos:
        deps[srpm_info['srcrpm']] = set()
        for dep in srpm_info['deps']:
            if dep in p_to_s_map:
                deps[srpm_info['srcrpm']].add(p_to_s_map[dep])
    return deps


def toposort2(data):
    # Ignore self dependencies.
    for key, val in data.items():
        val.discard(key)
    # Find all items that don't depend on anything.
    extra_items_in_deps = reduce(set.union,
                                 data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    extra = {}
    for item in extra_items_in_deps:
        extra[item] = set()
    data.update(extra)
    result = []
    while True:
        ordered = set(item for item, dep in data.iteritems() if not dep)
        if not ordered:
            break
        result.append(ordered)
        newdata = {}
        for item, dep in data.iteritems():
            if item not in ordered:
                newdata[item] = (dep - ordered)
        data = newdata
    assert not data, ("Cyclic dependencies exist among these items:\n%s" %
                      '\n'.join(repr(x) for x in data.iteritems()))
    return result


def write_rpmmacros():
    rpmmacros = open(os.path.join(RPM_TOP_DIR, '.rpmmacros'), 'w')
    rpmmacros.write('%%_topdir %s\n' % RPM_TOP_DIR)
    rpmmacros.write('%%_rpmdir %s\n' % TMP_RPM_PATH)
    rpmmacros.close()


def find_pkg(srpm_infos, srpm):
    for srpm_info in srpm_infos:
        if srpm_info["srcrpm"] == srpm:
            return srpm_info


def get_pkg_ddeps(deps, srpm):
    if srpm in deps:
        ddeps = []
        for dep in deps[srpm]:
            ddeps.append(dep)
            for ddep in get_pkg_ddeps(deps, dep):
                ddeps.append(ddep)
        return ddeps
    else:
        return []


def get_srpm_hash(srpm_infos, external, deps, srpm):
    allpkgs = get_pkg_ddeps(deps, srpm)
    allpkgs.append(srpm)
    allpkgs.sort()
    srpm_hash = hashlib.md5()
    for mypkg in allpkgs:
        srpm_info = find_pkg(srpm_infos, mypkg)
        srpm_hash.update(srpm_info['spec'])
    srpm_hash.update(external)
    return srpm_hash.hexdigest()


def get_cache_dir(srpm_infos, external, deps, srpm):
    if not os.path.exists(CACHE_DIR):
        return None
    myhash = get_srpm_hash(srpm_infos, external, deps, srpm)
    dst_dir = os.path.join(CACHE_DIR, myhash)
    return dst_dir


def need_to_build(srpm_infos, external, deps, srpm):
    dst_dir = get_cache_dir(srpm_infos, external, deps, srpm)
    if not dst_dir:
        return True
    return (not os.path.exists(dst_dir))


def get_new_number(srpm, cache_dir):
    if cache_dir == None:
        return 1
    latest_path = os.path.join(CACHE_DIR, srpm, "latest")
    if os.path.exists(latest_path):
        latest = int(os.readlink(latest_path))
        os.remove(latest_path)
        build_number = latest+1
    else:
        try:
            os.makedirs(os.path.join(CACHE_DIR, srpm))
        except os.error:
            pass
        build_number = 1

    os.symlink("%d" % build_number, latest_path)
    num_file_path = os.path.join(CACHE_DIR, srpm, "%d" % build_number)
    print "Creating: %s" % num_file_path
    num_file = open(num_file_path, 'w')
    num_file.write(cache_dir)
    num_file.close()
    return build_number


def createrepo():
    (ret, _, stderr) = doexec(["createrepo", "--update", RPMS_DIR])
    if ret != 0:
        print "Error running createrepo:"
        print stderr
        sys.exit(1)


def do_build(srpm, target, build_number, use_mock, xs_build_sys):
    print "Building %s - build number: %d" % (srpm, build_number)
    if use_mock:
        cmd = ["mock", "--configdir=mock", "-r", "xenserver",
               "--resultdir=%s" % TMP_RPM_PATH, "--rebuild",
               "--target", target,
               "--enable-plugin=tmpfs",
               "--define", "extrarelease .%d" % build_number,
               "-v", srpm]
        if not xs_build_sys:
            cmd = ["sudo"] + cmd + ["--disable-plugin=package_state"]
    else:
        cmd = ["rpmbuild", "--rebuild", "-v", "%s" % srpm,
               "--target", target, "--define",
               "_build_name_fmt %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm"]

    (ret, stdout, stderr) = doexec(cmd)

    if ret == 0:
        print "Success"
    else:
        print "Failed to build rpm from srpm: %s" % srpm
        print "\nstdout\n======\n%s" % stdout
        print "\nstderr\n======\n%s" % stderr
        sys.exit(1)

    return glob.glob(os.path.join(TMP_RPM_PATH, "*.rpm"))


def build_srpm(srpm, srpm_infos, external, deps, use_mock, xs_build_sys):
    cache_dir = get_cache_dir(srpm_infos, external, deps, srpm)

    if(need_to_build(srpm_infos, external, deps, srpm)):
        target = extract_target(srpm_infos, srpm)
        build_number = get_new_number(srpm, cache_dir)
        pkgs = do_build(srpm, target, build_number, use_mock, xs_build_sys)
        if cache_dir:
            os.makedirs(cache_dir)
            for pkg in pkgs:
                print "Copying output file %s to %s\n" % (pkg, cache_dir)
                shutil.copy(pkg, cache_dir)

    else:
        print "Not building %s - getting from cache" % srpm
        pkgs = glob.glob(os.path.join(cache_dir, "*.rpm"))
        for pkg in pkgs:
            print "Copying cached rpm %s to %s" % (pkg, TMP_RPM_PATH)
            shutil.copy(pkg, TMP_RPM_PATH)

    if not use_mock:
        (ret, _, stderr) = doexec(["rpm", "-U", "--force", "--nodeps"] + pkgs)
        if ret != 0:
            print "Ignoring failure installing rpm batch: %s" % pkgs
            print stderr

    for pkg in pkgs:
        print "Moving output RPM %s to %s\n" % (pkg, RPMS_DIR)
        shutil.move(pkg, RPMS_DIR)

    print "Success"
    createrepo()


def main():
    use_mock = False
    xs_build_sys = False
    try:
        longopts = ["use-mock", "xs-build-sys"]
        opts, _ = getopt.getopt(sys.argv[1:], "", longopts)
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(1)
    for opt, _ in opts:
        if opt == "--use-mock":
            use_mock = True
        if opt == "--xs-build-sys":
            xs_build_sys = True

    if not os.path.isdir(SRPMS_DIR) or not os.listdir(SRPMS_DIR):
        print ("Error: No srpms found in %s; First run configure.py." %
               SRPMS_DIR)
        sys.exit(1)

    packages = glob.glob(os.path.join(SRPMS_DIR, '*.src.rpm'))
    write_rpmmacros()
    srpm_infos = [get_srpm_info(pkg) for pkg in packages]
    deps = get_deps(srpm_infos)
    order = toposort2(deps)
    external = "external dependencies hash"

    for path in (TMP_RPM_PATH, BUILD_DIR, RPMS_DIR):
        if os.path.exists(path):
            print "Cleaning out directory: %s" % path
            shutil.rmtree(path)
        os.makedirs(path)
        os.chmod(path, 0777)

    createrepo()

    for batch in order:
        for srpm in batch:
            build_srpm(srpm, srpm_infos, external, deps, use_mock, xs_build_sys)


if __name__ == '__main__':
    main()
