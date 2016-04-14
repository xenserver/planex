# Planex [![Build Status](https://travis-ci.org/xenserver/planex.svg?branch=master)](https://travis-ci.org/xenserver/planex)

Planex is a toolkit for building collections of interdependent RPMs.  The main tools are:

* `planex-depend` - extracts dependencies from Spec files, in `make` format
* `planex-fetch` - downloads sources specified in Spec files
* `planex-cache` - similar to `ccache`, caches previous builds to speed up rebuilds
* `planex-pin` - for developers, overrides Spec file sources with local development repositories

Planex also contains a generic makefile which handles dependency resolution and sequences the build.   Partial rebuilds and concurrent builds are both supported.   By default, packages are built in `mock` chroots but this can be changed by overriding a variable in the makefile.

Planex runs on RedHat- and Debian-like Linux distributions.

## Usage


Building a Planex project is straightforward.   The Planex repository includes a small demo project:
```
cd planex-demo
make
```
See [the planex-demo README](planex-demo/README.md) for a more advanced tutorial, including how to use `planex-pin` for development.

## Installation from binary packages

#### CentOS 7
```bash
yum install epel-release
yum install https://xenserver.github.io/planex-release/release/rpm/el/planex-release-7-1.noarch.rpm
yum install planex
```

#### Fedora 21
```bash
yum install https://xenserver.github.io/planex-release/release/rpm/fedora/planex-release-21-1.noarch.rpm
yum install planex
```

## Installation from source

### Dependencies

#### CentOS 7
```bash
yum install epel-release yum-utils
yum-builddep planex.spec
```
#### Fedora 22
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
