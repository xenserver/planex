"""Classes for handling repositories holding source."""


import logging
import os.path
import subprocess
import urlparse


class Repository(object):
    """Represents a specific branch or tag of a repository"""

    def __init__(self, url):
        self.url = urlparse.urlparse(url)
        self.clone_url = None
        self.dir_name = ''
        self.branch = None
        self.tag = None
        if self.url.netloc in self.parsers:
            self.parsers[self.url.netloc](self)

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

    def parse_github(self):
        """Parse GitHub source URL"""
        path = self.url.path.split('/')
        self.clone_url = "ssh://git@%s/%s/%s.git" % (self.url.netloc, path[1],
                                                     path[2])
        self.dir_name = path[2]
        # Cannot diferentiate between a tag and a branch
        self.tag = path[4]

    def parse_bitbucket(self):
        """Parse BitBucket source URL"""
        path = self.url.path.split('/')
        self.clone_url = "ssh://git@%s/%s/%s.git" % (self.url.netloc, path[5],
                                                     path[7])
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
