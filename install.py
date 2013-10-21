#!/usr/bin/env python

import sys
import os
import glob
import subprocess
import shutil

import demjson
from planex_globals import RPMS_DIR

CONFIG = "install.json"


def parse_config(config_path):
    """Returns list of package names to install. These can be used in
    conjunction with rpm query to find the relevant .rpm files that need
    installing.
    """
    f = open(config_path, "r")
    json = f.read()
    f.close()
    pkgs = demjson.decode(json)
    return [pkg['package-name'] for pkg in pkgs]


def build_map(rpms_dir):
    """Returns a map from package name to rpm file"""
    result = {}
    for rpm_file in glob.glob(os.path.join(rpms_dir, '*.rpm')):
        pkg_name = subprocess.Popen(
            ["rpm", "-qp", rpm_file, "--qf", "%{name}"],
            stdout=subprocess.PIPE).communicate()[0].strip()
        result[pkg_name] = rpm_file
    return result


if __name__ == '__main__':
    if len(sys.argv[1:]) != 2:
        print "Usage: %s <component-dir> <destination-dir>" % __file__
        sys.exit(1)
    (component_dir, dest_dir) = sys.argv[1:]

    if not os.path.exists(component_dir):
        print "Error: directory %s does not exist." % p
        sys.exit(1)

    config_path = os.path.join(component_dir, CONFIG)
    if not os.path.exists(config_path):
        print ("Config file %s not found, assuming no RPMs need packaging." %
               config_path)
        sys.exit(0)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    config = parse_config(config_path)

    pkg_to_rpm = build_map(RPMS_DIR)

    for pkg_name in config:
        rpm_path = pkg_to_rpm[pkg_name]
        print "Copying:  %s -> %s" % (rpm_path, dest_dir)
        shutil.copy(rpm_path, dest_dir)
