# Planex

Scripts and libraries to build rpms

## Usage

This is an example run to demonstrate how you can build the software specified
by `xen-api-libs-specs`.

 * Clone a configuration
```bash
git clone https://github.com/xapi-project/xen-api-libs-specs
```
 * Apply a workaround [#42](https://github.com/xenserver/planex/issues/42)
```bash
grep --exclude-dir=".git" -lr "@VERSION@" xen-api-libs-specs/ |
while read fname; do sed -ie 's/@VERSION@/UNRELEASED/g' $fname; done
find xen-api-libs-specs/ -name '*.ine' -delete
```
 * Clone github repositories
```bash
mkdir ~/github_mirror
planex-clone xen-api-libs-specs ~/github_mirror
```
 * Configure
```bash
planex-configure --config-dir=xen-api-libs-specs
```
 * TODO: At the moment configure throws an error - this needs to be resolved

## Installation

### Dependencies

#### Ubuntu 12.04

```bash
sudo apt-get -qy install python-rpm rpm
```

#### CentOS 6.4

 * Basic dependencies:

```bash
yum -y install git rpm-python rpm-build
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

### Planex

To install PlanEx, clone this repository and run the following:

```bash
sudo python setup.py install
```

This will install 4 binaries:

* `planex-configure`
* `planex-build`
* `planex-install`
* `planex-clone`

## Testing

To run unittest, use `tox`:

```bash
$ tox
```

