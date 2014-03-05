This Git repository contains scripts which build XenServer domain 0 RPMs.

## Installation

### Dependencies

On an Ubuntu system:

```bash
$ sudo apt-get -qy install python-rpm rpm
```

To install PlanEx, clone this repository and run the following:

```bash
$ sudo python setup.py install
```

This will install 3 binaries in (typically) `/usr/local/bin/`:

* `planex-configure`
* `planex-build`
* `planex-install`

### Testing

To run unittest, use `tox`:

```bash
$ tox
```
