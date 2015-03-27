# Planex demo
This is an example directory structure that can be used with planex.

It contains just a collection of spec files in a directory called `SPECS` and
a bit of mock config.

The intention is that the `Makefile` here should just include the single line:

```make
include /usr/share/planex/Makefile.rules
```

However, there's currently a bit here to generate the mock config. The
intention is that this would move into `planex-init`.

## Contents
This demo contains two dummy packages, `dumb` and `dumber` where `dumber` has
a single dependency on `dumb`.

## Building the pacakages
These packages can be built as defined in the spec files simply by running
`make`:

```
$ make
```

## Pinning (using development overrides)
If you want to work on a package (say, the `dumb` package), you can do so using
the pinning mechanism.

First clone a working copy of the source for this package to a convenient
directory:

```
$ mkdir ../repos
$ git clone git://github.com/jonludlam/dumb.git ../repos/dumb
```

Now you can "pin" the `dumb` package to any git "tree-ish" (commit sha, branch,
tag) like so:

```
$ planex-pin add SPECS/dumb.spec ../repos/dumb#master
$ planex-pin list
* SPECS/dumb.spec -> ../repos/dumb#master
```

Now, typing `make` will build this package at this pin.

By default, `Source0` is "pinned" but you can choose to pin a different source
by specifying the `--source` option which takes a number.

### Multiple sources

There is another package in this demo: `dumbest` which has no dependencies but
requires multiple sources.

You can pin multiple sources and the versions of the repositories are composed
into a release for the pinned spec file. For example, I could do the following
with the `dumbest` package:

```
$ planex-pin add SPECS/dumbest.spec --source 0 ../repos/dumbest#bad8958
$ planex-pin add SPECS/dumbest.spec --source 1 ../repos/dumbest-extra#eaa4587
$ planex-pin list
* SPECS/dumbest.spec : Source0 -> ../repos/dumbest#bad8958
* SPECS/dumbest.spec : Source1 -> ../repos/dumbest-extra#eaa4587
$ make
...
[RPMBUILD] _build/SRPMS/dumbest-0.1-s0+0.1+1+gbad8958_s1+0.1+1+geaa4587.src.rpm
[CREATEREPO] _build/RPMS/x86_64/dumbest-0.1-s0+0.1+1+gbad8958_s1+0.1+1+geaa4587.x86_64.rpm
```
