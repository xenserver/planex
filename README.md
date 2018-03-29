# Planex [![Build Status](https://travis-ci.org/xenserver/planex.svg?branch=master)](https://travis-ci.org/xenserver/planex)

Planex is a toolkit for building medium-sized collections of RPM packages which may depend on each other.
It fills the gap between tools to build individual RPMs, such as `rpmbuild` and `mock`, and tools to build entire distributions, such as [koji](https://fedoraproject.org/wiki/Koji).

## Installing Planex 

The easiest way to install Planex is to use `pip` in a Python virtualenv.

Planex uses the Python bindings for `librpm`, which must be installed separately using the system package manager.
```
$ dnf install python2-rpm
```

If you want to install Planex in a virtualenv, remember to pass the `--system-site-packages` so the `librpm` bindings are available in the virtualenv.

```
$ virtualenv venv --system-site-packages
New python executable in /tmp/venv/bin/python2
Also creating executable in /tmp/venv/bin/python
Installing setuptools, pip, wheel...done.
$ source venv/bin/activate
```

Clone the source, install the requirements and install Planex
```
$ git clone https://github.com/xenserver/planex
Cloning into 'planex'...
remote: Counting objects: 11951, done.
remote: Compressing objects: 100% (78/78), done.
remote: Total 11951 (delta 143), reused 176 (delta 130), pack-reused 11743
Receiving objects: 100% (11951/11951), 2.17 MiB | 931.00 KiB/s, done.
Resolving deltas: 100% (8368/8368), done.
$ cd planex
$ pip install -r requirements.txt
...
$ python setup.py install
```

For development work, also install the test requirements and use `python setup.py develop`, which symlinks the code so you do not have to run `python setup.py install` after every edit.
```
$ pip install -r test-requirements.txt
...
$ python setup.py develop
$ nosetests
```

## Defining which packages to build

The main input to Planex is a repository containing RPM spec files, possibly a few source files and a small Makefile.
```
.
├── Makefile
├── SOURCES
│   └── bar
│       └── bar.service
└── SPECS
    ├── bar.spec
    ├── bar.lnk
    └── foo.spec
```

Each spec file describes the sources needed to build a package, any other packages which are required to build it, how to build it and how to pack the resulting files into a binary package.
Most package sources are not kept with the spec files - instead `planex-fetch` downloads them from the URLs given in the spec files.
The source files could be static files on HTTP servers or tarballs produced dynamically by source control systems such as GitHub or BitBucket.
A few sources can be kept in the spec file directory - these could be small temporary patches or resources such as SystemD service files which do not really belong anywhere else.
This approach is not suitable for large numbers of frequently-changing extra sources, such as patchqueues.


## Overriding and augmenting packages

If a package relies on a source file which is not fully defined in its spec file, `planex-fetch` will not know where to get it.
One way around this problem is to change the spec file to contain a full URL for the source, however if the spec file is for an upstream package which we just re-build we may not want to change it.
Planex's solution to this is to add a 'link' file which defines additional sources to fetch and build into the package.
The link file can modify the sources listed in the spec in several ways:

   * provide the URL of a source which does not have one
   * override a source URL in the spec file - for instance to use a local mirror instead of a public repository
   * provide the URL of a tarball of source files which are required by the package
   * provide the URL of a tarball containing a patchqueue which will be added to any patches already defined by the spec file

For development, it is also possible to override a source listed in the spec with the contents of a Git repository.
To do this, create a link file with a `.pin` extension in the `PINS` directory.
This will cause `planex-fetch` to make a tarball archive of the repository and use it in place of the tarball specified in the spec file.
