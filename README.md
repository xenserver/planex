# Planex [![Build Status](https://travis-ci.org/xenserver/planex.svg?branch=master)](https://travis-ci.org/xenserver/planex)

Planex is a toolkit for building collections of interdependent RPMs.  The main tools are:

* `planex-depend` - extracts dependencies from Spec files, in `make` format
* `planex-fetch` - downloads sources specified in Spec files
* `planex-cache` - similar to 'ccache', caches previous builds to speed up rebuilds
* `planex-pin` - for developers, overrides Spec file sources with local development repositories

Planex also contains a generic makefile which handles dependency resolution and sequences the build.   Partial rebuilds and concurrent builds are both supported.   By default, packages are built in `mock` chroots but this can be changed by overriding a variable in the makefile.

Planex runs on RedHat- and Debian-like Linux distributions.   On Debian, the `planex-makedeb` tool can generate source packages which can be passed to `cowbuilder` to produce binary `.deb' packages.   The makefile has rules to sequence Debian package builds, but `planex-cache` cannot be used.

## Usage

This is an example run to demonstrate how you can build the software specified
in the planex-demo subdirectory

 * Change directory to planex-demo
```bash
cd planex-demo
```
 * Clone the repositories specified in the spec files
```bash
planex-clone
```
 * Configure
```bash
planex-configure
```
 * Build
```bash
make
```

## Installation

### Dependencies

#### Ubuntu 14.04

```bash
sudo apt-get -qy install python-rpm python-setuptools python-argparse rpm
```

#### CentOS 6

 * Basic dependencies:

```bash
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
rpm -Uvh epel-release-6-8.noarch.rpm
yum -y install git rpm-python rpm-build mock python-setuptools python-argparse
```
 * Pip:
```bash
wget --no-check-certificate https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
pip install virtualenv
virtualenv --system-site-packages env
. env/bin/activate
pip install -r requirements.txt
```

## Testing

To run unit tests, use `tox`:

```bash
$ tox
```
