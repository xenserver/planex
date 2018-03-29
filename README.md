# Planex [![Build Status](https://travis-ci.org/xenserver/planex.svg?branch=master)](https://travis-ci.org/xenserver/planex)

Planex is a toolkit for building medium-sized collections of RPM packages which may depend on each other.
It fills the gap between tools to build individual RPMs, such as `rpmbuild` and `mock`, and tools to build entire distributions, such as [koji](https://fedoraproject.org/wiki/Koji).

## Installation 

### Pip

Planex uses the Python bindings for `librpm`, which must be installed separately.
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
