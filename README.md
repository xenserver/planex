# Planex

Scripts and libraries to build rpms

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
sudo apt-get -qy install python-rpm rpm
```

#### CentOS 6

 * Basic dependencies:

```bash
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
rpm -Uvh epel-release-6-8.noarch.rpm
yum -y install git rpm-python rpm-build mock
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

This will install the planex binaries:

* `planex-configure`
* `planex-build`
* `planex-clone`
* `planex-specdep`
* and a few others

## Testing

To run unit tests, use `tox`:

```bash
$ tox
```
