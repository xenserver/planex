#!/usr/bin/env python

"""
Installs packages built from the specs in <component-specs-dir>.
"""


import sys
import os
import subprocess
import shutil
import argparse

from collections import namedtuple

import json
from planex.globals import RPMS_DIR

CONFIG = "install.json"


ExecutionResult = namedtuple('ExecutionResult', 'return_code, stdout, stderr')


class SpecsDir(object):
    def __init__(self, root):
        self.root = root

    @property
    def has_install_config(self):
        return self.root.isfile(self.install_config_path)

    @property
    def install_config_path(self):
        return CONFIG

    @property
    def install_config_syspath(self):
        return self.root.getsyspath(self.install_config_path)

    @property
    def install_config_is_json(self):
        contents = self.root.getcontents(self.install_config_path)
        try:
            json.loads(contents)
            return True
        except ValueError:
            return False

    def get_package_names_to_install(self):
        pkgs = json.loads(self.root.getcontents(self.install_config_path))
        return [pkg['package-name'] for pkg in pkgs]


class FakeExecutor(object):
    def __init__(self):
        self.results = {}

    def run(self, args):
        assert tuple(args) in self.results, "Unexpected call %s" % args
        return self.results[tuple(args)]

    def map_rpmname_query(self, rpm_syspath, name):
        self.results[(
            'rpm', '-qp', rpm_syspath, '--qf', '%{name}'
        )] = ExecutionResult(
            return_code=0,
            stdout=name,
            stderr='ignored')


class RealExecutor(object):
    def run(self, args):
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        return ExecutionResult(
            return_code=proc.returncode,
            stdout=out,
            stderr=err)


class RPMPackage(object):
    def __init__(self, rpmsdir, path):
        self.path = path
        self.rpmsdir = rpmsdir

    def get_name(self):
        result = self.rpmsdir.executor.run(
            ['rpm', '-qp', self.syspath, '--qf', '%{name}'])
        return result.stdout.strip()

    @property
    def syspath(self):
        return self.rpmsdir.root.getsyspath(self.path)


class RPMSDir(object):
    def __init__(self, root, executor):
        self.root = root
        self.executor = executor

    @property
    def rpms(self):
        rpms = []
        for rpm_path in self.root.listdir(wildcard='*.rpm'):
            rpms.append(RPMPackage(self, rpm_path))
        return rpms

    def build_map(self):
        """Returns a map from package name to rpm package"""
        result = {}
        for rpm in self.rpms:
            pkg_name = rpm.get_name()
            result[pkg_name] = rpm
        return result


def parse_args_or_exit(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('component_dir', help='Specs directory')
    parser.add_argument('dest_dir', help='Destination directory')
    return parser.parse_args(argv)


def directory_exists(path):
    return os.path.exists(path) and os.path.isdir(path)


def main():
    """Main entry point.   Installs packages from <component-dir>
    to <destination-dir>"""

    args = parse_args_or_exit()

    if not directory_exists(args.component_dir):
        print "Error: directory %s does not exist." % args.component_dir
        sys.exit(1)

    specs_dir = SpecsDir(args.component_dir)
    if not specs_dir.has_install_config:
        print ("Config file %s not found, assuming no RPMs need installation." %
               specs_dir.install_config_syspath)
        sys.exit(0)

    if not directory_exists(args.dest_dir):
        os.makedirs(args.dest_dir)

    rpms_dir = RPMSDir(RPMS_DIR, RealExecutor())

    package_names = specs_dir.get_package_names_to_install()

    pkg_to_rpm = rpms_dir.build_map()

    for pkg_name in package_names:
        rpm_path = pkg_to_rpm[pkg_name].syspath
        print "Copying:  %s -> %s" % (rpm_path, args.dest_dir)
        shutil.copy(rpm_path, args.dest_dir)
