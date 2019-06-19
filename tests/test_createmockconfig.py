"""
Tests for createmockconfig
"""

import argparse
import re
import unittest
import fnmatch
import mock
from nose.tools import nottest

import planex.cmd.createmockconfig as createmockconfig


def compile_pattern(pat, ignore_case=False):
    """mock function for misc.compile_pattern"""
    if re.compile(r'[*?]|\[.+\]').search(pat):
        try:
            flags = re.I if ignore_case else 0
            return re.compile(fnmatch.translate(pat), flags).match
        except re.error:
            pass  # fall back to exact match
    if ignore_case:
        pat = pat.lower()
        return lambda s: s.lower() == pat
    return lambda s: s == pat


class MockYumBase(object):
    """mock class for yum.YumBase"""
    # pylint: disable=R0903
    def __init__(self):
        self.repos = MockYumBaseRepos()


class MockRepo(object):
    """mock class for repo"""
    # pylint: disable=R0903,C0103
    def __init__(self, name="", repoid="", enabled=True):
        self.id = repoid
        self.name = name
        self.enabled = enabled
        self.priority = 99


class MockYumBaseRepos(object):
    """mock class for yum.YumBase().repos"""
    # pylint: disable=C0103
    def __init__(self):
        self.repos = [MockRepo("base", "base"),
                      MockRepo("extras", "extras"),
                      MockRepo("updates", "updates"),
                      MockRepo("TestAAA", "TestAAA", False),
                      MockRepo("TestBBB", "TestBBB", False)]

    def listEnabled(self):
        """mock function for yum.YumBase().repos.listEnabled"""
        return [x for x in self.repos if x.enabled]

    def findRepos(self, pattern, ignore_case=False):
        """mock function for yum.YumBase().repos.findRepos"""
        if pattern in self.repos:  # Minor opt. as we do this a lot...
            return [self.repos[pattern]]

        result = []

        for item in pattern.split(','):
            item = item.strip()
            match = compile_pattern(item.strip(), ignore_case)
            for repo in self.repos:
                if match(repo.id):
                    result.append(repo)

        return result


class BasicTests(unittest.TestCase):
    """Basic createmockconfig tests"""
    @nottest
    def common_load_yum_repo_test(self, test_args, expected_list):
        """common test steps for load_yum_repo"""
        test_args = '--configdir ./ -r mockroot ' + test_args + 'X'
        test_argv = test_args.split(' ')
        args = createmockconfig.parse_args_or_exit(test_argv)
        result_list = createmockconfig.load_yum_repos(args.repo_config_list)
        self.assertEqual(set(expected_list), {x.id for x in result_list})

    @mock.patch('planex.cmd.createmockconfig.yum.YumBase')
    @mock.patch('planex.cmd.createmockconfig.common_base_parser')
    def test_load_yum_repo(self, mock_common_base_parser, mock_yum_base):
        """testcase for load_yum_repo"""
        mock_common_base_parser.return_value = \
            argparse.ArgumentParser(add_help=False)
        mock_yum_base.return_value = MockYumBase()

        self.common_load_yum_repo_test(
            '--disablerepo * --enablerepo updates ',
            ["updates"])
        self.common_load_yum_repo_test(
            '--enablerepo updates --disablerepo * ',
            [])
        self.common_load_yum_repo_test(
            '--enablerepo * ',
            ["base", "extras", "updates", "TestAAA", "TestBBB"])
        self.common_load_yum_repo_test(
            '--disablerepo * --enablerepo Test* ',
            ["TestAAA", "TestBBB"])
        self.common_load_yum_repo_test(
            '',
            ["base", "extras", "updates"])
