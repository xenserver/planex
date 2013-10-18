#!/usr/bin/env python

import sys
import os

component = os.getenv("COMPONENT")

if component == "ocaml":
    print "/repos/xen-dist-ocaml.hg"
elif component == "api-libs":
    print "/repos/xen-api-libs-specs"
elif component == "api-backports":
    print "/repos/xen-api-backports"
else:
    sys.stderr.write("Unknown component: '%s'\n" % component)
    sys.exit(1)
