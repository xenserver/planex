"""Classes for handling repositories holding source."""


import logging
import os.path
import subprocess
import urlparse
import re

from planex.util import git_ls_remote


class Repository(object):
    """Represents a specific branch or tag of a repository"""

    def __init__(self, url):
        self.url = urlparse.urlparse(url)
        self.clone_url = None
        self._query_url = None
        self.dir_name = ''
        self.branch = None
        self.tag = None
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
        branch_or_tag = self.tag or self.branch
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
            return urlparse.urlunparse(self.url)
        ret = "url=" + self.clone_url
        if self.branch:
            ret += "&branch=" + self.branch
        if self.tag:
            ret += "&tag=" + self.tag
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
        else:
            option = '-h'
            ref = self.branch

        # Example command:
        # git ls-remote -t \
        #     git://hg.uk.xensource.com/carbon/trunk/blktap.git v3.3.0*
        remote_refs = git_ls_remote(self._query_url, ref + '*', option)

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

        remote_ref = git_ls_remote(self._query_url, path[4])

        if remote_ref.split('/', 2)[1] == 'tags':
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
        query_str = urlparse.unquote(self.url.query)
        if query_str.startswith('at='):
            query = query_str[3:]
            if '&' in query:
                query = query[:query.find('&')]
            query_path = query.split('/')
            if query_path[1] == 'tags':
                self.tag = query_path[2]
            elif query_path[1] == 'heads':
                self.branch = query_path[2]
            else:
                self.branch = 'master'
        else:
            self.branch = 'master'

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
