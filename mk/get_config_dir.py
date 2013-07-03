#!/usr/bin/env python

import os

component = os.getenv("COMPONENT")

if component == "ocaml":
    print "/repos/xen-dist-ocaml.hg"
if component == "api-libs":
    print "/repos/xen-api-libs-specs"

