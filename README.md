# Planex [![Build Status](https://travis-ci.org/xenserver/planex.svg?branch=master)](https://travis-ci.org/xenserver/planex)

Planex is a toolkit for building collections of interdependent RPMs.  The main tools are:

* `planex-depend` - extracts dependencies from Spec files, in `make` format
* `planex-fetch` - downloads sources specified in Spec files
* `planex-cache` - similar to `ccache`, caches previous builds to speed up rebuilds

Planex also contains a generic makefile which handles dependency resolution and sequences the build.   Partial rebuilds and concurrent builds are both supported.   By default, packages are built in `mock` chroots but this can be changed by overriding a variable in the makefile.

Planex runs on RedHat- and Debian-like Linux distributions.

## Installation from binary packages

#### CentOS 7
```bash
yum install epel-release
yum install https://xenserver.github.io/planex-release/release/rpm/el/planex-release-7-1.noarch.rpm
yum install planex
```

#### Fedora 23
```bash
yum install https://xenserver.github.io/planex-release/release/rpm/fedora/planex-release-23-1.noarch.rpm
yum install planex
```

## Installation from source

### Dependencies

#### CentOS 7
```bash
yum install epel-release yum-utils
yum-builddep planex.spec
```
#### Fedora 23
```bash
dnf builddep planex.spec
```
#### Ubuntu 14.04
```bash
apt-get -qy install python-rpm python-setuptools python-argparse rpm
```

#### Build and test
```bash
python setup.py build
nosetests
```
#### Install
```bash
python setup.py install
```
