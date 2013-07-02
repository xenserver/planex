#!/usr/bin/env python

# Build a bunch of SRPMs

import os, glob, subprocess, sys
import rpm
import demjson


class RpmError(Exception):
	pass
 
path = "SRPMS"

def exists(path):
    return os.access(path,os.F_OK)

def doexec(args, inputtext=None):
    """Execute a subprocess, then return its return code, stdout and stderr"""
    proc = subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    (stdout,stderr) = proc.communicate(inputtext)
    rc = proc.returncode
    return (rc,stdout,stderr)

def run_srpmutil(specfile,srpm):
    for x in ['i686','i386','noarch']:
	(rc,stdout,stderr) = doexec(["srpmutil/srpmutil",specfile,srpm,x])
	if(rc==0):
	    return (stdout,x)
    raise RpmError

def get_srpm_info(srpm):
    """ Returns a dictionary of interesting info about an SRPM:

    {
    "arch": "i686",
    "deps": [
      "ocaml",
      "ocaml-findlib",
      "ocaml-fd-send-recv-devel",
      "ocaml-uuidm-devel"
    ],
    "packages": [
      {
        "arch": "i686",
        "name": "ocaml-stdext-devel",
        "noarch": "0",
        "release": "1",
        "version": "0.9.0"
      },
      {
        "arch": "i686",
        "name": "ocaml-stdext-debuginfo",
        "noarch": "0",
        "release": "1",
        "version": "0.9.0"
      }
    ],
    "srcrpm": "SRPMS/ocaml-stdext-0.9.0-1.src.rpm"
    }

    """
    for x in glob.glob("SPECS/*.spec"):
        os.unlink(x)
    (rc,stdout,stderr) = doexec(["rpm","-i",srpm])
    myspecfile = glob.glob("/tmp/rpmbuild/SPECS/*.spec")[0]	 
    try:
	(specfile,arch) = run_srpmutil(myspecfile,srpm) 
	j = demjson.decode(specfile)
	(rc,stdout,stderr) = doexec(["rpm","-qp",srpm,"-R"])
	lines = stdout.split('\n')
	alldeps = map(lambda x: x.split(' ')[0], lines)
	realdeps = filter(lambda x: len(x) <> 0 and x<>"rpmlib(CompressedFileNames)",alldeps)
	j['deps']=realdeps
	j['arch']=arch
	return j
    except:
	return {'broken':True,'srcrpm':srpm}

def get_package_to_srpm_map(srpm_info):
    m = {}
    for srpm in srpm_info:
        for package in srpm['packages']:
            m[package['name']] = srpm['srcrpm']
    return m

def get_deps(srpm_info):
    p_to_s_map = get_package_to_srpm_map(srpm_info)
    deps = {}
    for srpm in srpm_info:
        deps[srpm['srcrpm']] = set()
        for dep in srpm['deps']:
            if p_to_s_map.has_key(dep):
                deps[srpm['srcrpm']].add(p_to_s_map[dep])
    return deps

def toposort2(data):
    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)
    # Find all items that don't depend on anything.
    extra_items_in_deps = reduce(set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    extra = {}
    for item in extra_items_in_deps:
        extra[item]=set()
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
    assert not data, "Cyclic dependencies exist among these items:\n%s" % '\n'.join(repr(x) for x in data.iteritems())
    return result


if __name__ == "__main__":
    packages = glob.glob( os.path.join(path, '*.src.rpm'))
    srpm_info = map(get_srpm_info, packages)
    deps = get_deps(srpm_info)
    order = toposort2(deps)

    for batch in order:
        for srpm in batch:
            print "Building %s" % srpm
            (rc,stdout,stderr) = doexec(["rpmbuild","--rebuild","%s" % srpm])
            if rc==0:
                print "Success"
            else:
                print "Failure"
