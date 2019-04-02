"""Classes for handling repositories holding source."""


import logging
import os.path
import subprocess
import requests

import pkg_resources

import planex.git as git
from planex.util import add_custom_headers_for_url

# pylint: disable=relative-import
from six.moves.urllib.parse import parse_qs, urlparse, urlunparse


class Repository(object):
    """Represents a specific branch or tag of a repository"""

    # pylint: disable=R0902

    def __init__(self, url):
        self.url = urlparse(url)
        self.clone_url = None
        self._query_url = None
        self.dir_name = ''
        self.branch = None
        self.tag = None
        self.commitish = None
        self.sha1 = None
        self.archive_at = None
        if self.url.netloc in self.parsers:
            self.parsers[self.url.netloc](self)
            self._populate_sha1()

    def clone(self, topdir, dirname=None):
        """Clone repository to a directory"""
        if dirname:
            out_dir = os.path.join(topdir, dirname)
        else:
            out_dir = os.path.join(topdir, self.dir_name)
        branch_or_tag = self.tag or self.branch or self.commitish
        cmd = ['git', 'clone']
        if branch_or_tag:
            cmd += ['--branch', branch_or_tag]
        cmd.append(self.clone_url)
        if dirname:
            cmd.append(dirname)
        logging.debug("Cloning %s#%s to %s", self.clone_url, branch_or_tag,
                      out_dir)
        subprocess.check_call(cmd, cwd=topdir)
        return out_dir

    def __repr__(self):
        """Textual representation of an object"""
        if self.clone_url is None:
            return urlunparse(self.url)
        ret = "url=" + self.clone_url
        if self.branch:
            ret += "&branch=" + self.branch
        if self.tag:
            ret += "&tag=" + self.tag
        if self.commitish:
            ret += "&id=" + self.commitish
        return ret

    def _populate_sha1(self):
        """Populate 'sha1' with the hash of the last commit.

        If the url is pointing to a branch, this will be the
        SHA1 of the latest commit.
        If the url is pointing to a tag, this will be the
        SHA1 of the commit tag is pointing to.
        """
        if self.url.netloc in self.tag_to_sha1s:
            to_sha1 = self.tag_to_sha1s[self.url.netloc]
            self.sha1 = to_sha1(self, self.archive_at)

        if not self.sha1 and self.url.netloc in self.branch_to_sha1s:
            to_sha1 = self.branch_to_sha1s[self.url.netloc]
            self.sha1 = to_sha1(self, self.archive_at)

        if not self.sha1 and self.url.netloc in self.commitish_to_sha1s:
            to_sha1 = self.commitish_to_sha1s[self.url.netloc]
            self.sha1 = to_sha1(self, self.archive_at)

        if not self.sha1:
            self.sha1 = ''

    def parse_github(self):
        """Parse GitHub source URL"""
        path = self.url.path.split('/')
        self.clone_url = "ssh://git@%s/%s/%s.git" % (self.url.netloc, path[1],
                                                     path[2])
        self.dir_name = path[2]

        self._query_url = '{}://{}/{}/{}/'.format(
            self.url.scheme,
            self.url.netloc,
            path[1],
            path[2]
        )

        remote_ref = git.ls_remote(self._query_url, path[4])

        if remote_ref and remote_ref.split('/', 2)[1] == 'tags':
            self.tag = path[4]
        else:
            self.branch = path[4]

    def parse_bitbucket(self):
        """Parse BitBucket source URL"""
        path = self.url.path.split('/')
        self.clone_url = "ssh://git@%s/%s/%s.git" % (self.url.netloc, path[5],
                                                     path[7])

        self._query_url = '{}://{}/scm/{}/{}.git'.format(
            self.url.scheme,
            self.url.netloc,
            path[5],
            path[7]
        )

        self.dir_name = path[7]
        query_dict = parse_qs(self.url.query)
        if 'at' in query_dict:
            query = query_dict['at'][0]
            self.archive_at = query
            if '/' in query:
                query_path = query.split('/')
                if query_path[1] == 'tags':
                    self.tag = query_path[2]
                elif query_path[1] == 'heads':
                    self.branch = '/'.join(query_path[2:])
                else:
                    self.branch = query
            else:
                self.commitish = query
        else:
            self.branch = 'master'

    @staticmethod
    def get_requests_headers(netloc):
        """
        Gets the HTTP headers for making requests to the specified location
        """
        useragent = ("planex-repository/%s" %
                     pkg_resources.require("planex")[0].version)
        headers = requests.utils.default_headers()
        headers.update({
            "user-agent": useragent,
        })
        add_custom_headers_for_url(netloc, headers)
        return headers

    def commitish_to_sha1_bitbucket(self, commitish):
        """Convert a commitish to a full SHA1 using the BitBucket API"""
        path = self.url.path.split('/')
        url = "https://%s/rest/api/1.0/projects/%s/repos/%s/commits/%s" % \
            (self.url.netloc, path[5], path[7], commitish)
        logging.debug("Fetching SHA1 using " + url)
        api_response = requests.get(
            url,
            headers=Repository.get_requests_headers(self.url.netloc))
        api_response.raise_for_status()
        data = api_response.json()
        return data['id']

    def branch_to_sha1_bitbucket(self, branch):
        """Convert a branch id to the full SHA1 of its latest commit using
        the REST API
        """
        path = self.url.path.split('/')
        url = "https://%s/rest/api/1.0/projects/%s/repos/%s/branches" % \
            (self.url.netloc, path[5], path[7])
        logging.debug("Fetching branches using " + url)
        api_response = requests.get(
            url,
            headers=Repository.get_requests_headers(self.url.netloc))
        api_response.raise_for_status()
        data = api_response.json()
        commit = [value['latestCommit'] for value in data['values']
                  if value['displayId'] == branch]
        return commit[0] if commit else None

    def tag_to_sha1_bitbucket(self, tag):
        """Convert a tag id to the full SHA1 of its latest commit using
        the REST API
        """
        path = self.url.path.split('/')
        url = "https://%s/rest/api/1.0/projects/%s/repos/%s/tags/%s" % \
            (self.url.netloc, path[5], path[7], tag)
        logging.debug("Fetching tags using " + url)
        api_response = requests.get(
            url,
            headers=Repository.get_requests_headers(self.url.netloc))
        api_response.raise_for_status()
        data = api_response.json()
        return data['latestCommit']

    def parse_gitweb(self):
        """Parse GitWeb source URL"""
        path = self.url.path.split('/')
        self.clone_url = "git://%s/%s" % (self.url.netloc, '/'.join(path[2:5]))
        self._query_url = self.clone_url
        self.dir_name, _ = os.path.splitext(path[4])
        if path[7] == 'tags':
            self.tag = path[8]
            for suffix in ('.tar.gz', '.tar.bz2'):
                if self.tag.endswith(suffix):
                    self.tag = self.tag[:-len(suffix)]
        else:
            self.branch = 'master'

    parsers = {
        'github.com': parse_github,
        'code.citrite.net': parse_bitbucket,
        'hg.uk.xensource.com': parse_gitweb,
        }
    commitish_to_sha1s = {
        'code.citrite.net': commitish_to_sha1_bitbucket
    }
    branch_to_sha1s = {
        'code.citrite.net': branch_to_sha1_bitbucket
    }
    tag_to_sha1s = {
        'code.citrite.net': tag_to_sha1_bitbucket
    }

    def repository_url(self):
        """
        Return the first non-null value among self.clone_url and
        self.url as a readable url. If they are all None, it returns None.
        """
        if self.clone_url is not None:
            return self.clone_url
        if self.url is not None:
            return urlunparse(self.url)

    def commitish_tag_or_branch(self):
        """
        Return the first non-null value among the repository commitish,
        tag or branch. If they are all None, it returns None.
        """
        if self.commitish is not None:
            return self.commitish
        if self.tag is not None:
            return self.tag
        if self.branch is not None:
            return self.branch
