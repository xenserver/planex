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
