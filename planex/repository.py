"""Classes for handling repositories holding source."""


import logging
import os.path
import subprocess
import re
import requests

import planex.git as git

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
        if self.tag:
            option = '-t'
            ref = self.tag
        elif self.branch:
            option = '-h'
            ref = self.branch
        elif self.commitish and self.url.netloc in self.commitish_to_sha1s:
            commitish_to_sha1 = self.commitish_to_sha1s[self.url.netloc]
            self.sha1 = commitish_to_sha1(self, self.commitish)
            return
        else:
            self.sha1 = ''
            return

        # Example command:
        # git ls-remote -t \
        #     git://hg.uk.xensource.com/carbon/trunk/blktap.git v3.3.0*
        remote_refs = git.ls_remote(self._query_url, ref + '*', option)

        # Example output of above command:
        # db8d9edd203460adba4b9175971c2cfc14ac0f64  refs/tags/v3.3.0
        # ddb48b561342d7742ec1dbd6c4987c1f4add9387  refs/tags/v3.3.0^{}
        regex = (
            r'(^[\da-f]{{40}})'     # 40 char hex SHA1 (group(1))
            r'\trefs\/'             # <tab>refs/
            r'(?:tags|heads)\/'     # {'tags' or 'heads'}/
            '({}(\\^{{}})*)$'       # <ref>{0 or more of '^{}'} (group(2))
        ).format(re.escape(ref))

        # list of (<ref_name>, <sha1>) tuples
        ref_sha1_list = []

        for line in remote_refs.split('\n'):
            match = re.match(regex, line)

            if match is not None:
                ref_sha1_list.append((match.group(2), match.group(1)))

        if ref_sha1_list:
            # Sort in descending order by <ref_name> length;
            # This way, names with '^{}' will come to the beginning
            # of the list. Their SHA1 points to the actual commit
            # instead of the tag object.
            ref_sha1_list.sort(key=lambda tup: len(tup[0]), reverse=True)
            self.sha1 = ref_sha1_list[0][1]
        else:
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
            if '/' in query:
                query_path = query.split('/')
                if query_path[1] == 'tags':
                    self.tag = query_path[2]
                elif query_path[1] == 'heads':
                    self.branch = query_path[2]
                else:
                    self.branch = 'master'
            else:
                self.commitish = query
        else:
            self.branch = 'master'

    def commitish_to_sha1_bitbucket(self, commitish):
        """Convert a commitish to a full SHA1 using the BitBucket API"""
        path = self.url.path.split('/')
        url = "https://%s/rest/api/1.0/projects/%s/repos/%s/commits/%s" % \
            (self.url.netloc, path[5], path[7], commitish)
        logging.debug("Fetching SHA1 using " + url)
        api_response = requests.get(url)
        api_response.raise_for_status()
        data = api_response.json()
        return data['id']

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
