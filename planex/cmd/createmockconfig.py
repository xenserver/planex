"""
planex-create-mock-config: Populate mock config with yum repositories
"""

from __future__ import print_function
import argparse
import ast
import ConfigParser
import os
import os.path
import pprint
import StringIO

import yum
import argcomplete

from planex.cmd.args import common_base_parser
from planex.util import setup_logging
from planex.util import setup_sigint_handler


class DictAction(argparse.Action):
    """
    Action subclass to form a dict from a sequence of arguments
    """
    # pylint: disable=R0903
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(DictAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if '=' not in values:
            raise ValueError("invalid option: "+values)
        key, value = values.split('=', 1)
        dictvalue = getattr(namespace, self.dest)
        if dictvalue is None:
            dictvalue = {}
        dictvalue[key] = ast.literal_eval(value)
        setattr(namespace, self.dest, dictvalue)


class RepoAction(argparse.Action):
    """
    Action subclass to form common function to add new repo config
    """
    # pylint: disable=R0903,W0223
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        dest = "repo_config_list"
        super(RepoAction, self).__init__(option_strings, dest, **kwargs)

    def sub_call(self, namespace, values, repo_config='enable'):
        """
        A common function to implement __call__
        """
        repo_config_list = getattr(namespace, self.dest)
        if repo_config_list is None:
            repo_config_list = []
        repo_config_list.append((repo_config, values))
        setattr(namespace, self.dest, repo_config_list)


class EnableRepoAction(RepoAction):
    """
    RepoAction subclass to form adding a enablement repo config
    """
    # pylint: disable=R0903
    def __call__(self, parser, namespace, values, option_string=None):
        self.sub_call(namespace, values, "enable")


class DisableRepoAction(RepoAction):
    """
    RepoAction subclass to form adding a disablement repo config
    """
    # pylint: disable=R0903
    def __call__(self, parser, namespace, values, option_string=None):
        self.sub_call(namespace, values, "disable")


def load_mock_reference(fname):
    """
    read in the reference mock configuration

    Chroot configurations are fragments of Python that mock `exec`s, mock goes
    to some lengths to make this less insecure but they are rather convoluted.
    We just trust that the caller has not included any surprises in the file.
    """
    config_opts = {}
    execfile(fname)
    return config_opts


def load_yum_repos(repo_config_list):
    """
    read in the yum repository configuration
    """
    yum_base = yum.YumBase()
    repo_set = {repo for repo in yum_base.repos.findRepos('*')
                if repo.enabled}
    for config, pattern in repo_config_list:
        if config == "enable":
            repo_set |= set(yum_base.repos.findRepos(pattern))
        elif config == "disable":
            repo_set -= set(yum_base.repos.findRepos(pattern))

    return list(repo_set)


def update_mock_repos(config, yum_repos, yum_config_opt):
    """
    Replace all repository sections with a new one derived from yum
    """
    for section in [s for s in config.sections() if s != 'main']:
        config.remove_section(section)
    for repo in yum_repos:
        config.add_section(repo.id)
        config.set(repo.id, 'name', repo.name)
        if repo.baseurl:
            config.set(repo.id, 'baseurl', ' '.join(repo.baseurl))
        else:
            config.set(repo.id, 'mirrorlist', repo.mirrorlist)
        if repo.gpgcheck:
            config.set(repo.id, 'gpgcheck', '1')
            config.set(repo.id, 'gpgkey', ' '.join(repo.gpgkey))
        else:
            config.set(repo.id, 'gpgcheck', '0')
        if repo.includepkgs:
            config.set(repo.id, 'includepkgs', ' '.join(repo.includepkgs))
        if repo.exclude:
            config.set(repo.id, 'exclude', ' '.join(repo.exclude))

        if yum_config_opt:
            for key, value in yum_config_opt.items():
                config.set('main', key, str(value))


def write_mock_cfg(fileh, cfg):
    """
    Save the mock configuration to a file handle
    """
    for key, value in cfg.items():
        if key in ('dnf.conf', 'yum.conf'):
            print('config_opts[\'%s\'] = """\n%s"""' % (key, value),
                  file=fileh)
        else:
            pretty = pprint.PrettyPrinter()
            print("config_opts['%s'] = %s" % (key, pretty.pformat(value)),
                  file=fileh)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Create mock config',
                                     parents=[common_base_parser()])
    parser.add_argument("mockconfig", metavar="OUTCFG",
                        help="output file")
    parser.add_argument("--configdir", metavar="CONFIGDIR", required=True,
                        help="mock config directory")
    parser.add_argument("-r", "--root", metavar="INCFG", required=True,
                        help="reference chroot config")
    parser.add_argument("--enablerepo", action=EnableRepoAction, default=[],
                        help="Repository to include")
    parser.add_argument("--disablerepo", action=DisableRepoAction, default=[],
                        help="Repository to exclude")
    parser.add_argument("--config_opt", action=DictAction, metavar="OPT=VALUE",
                        help="Define mock configuration settings")
    parser.add_argument("--yum-config_opt", action=DictAction,
                        metavar="OPT=VALUE",
                        help="Define yum/dnf configuration settings")
    parser.add_argument("--environment", action=DictAction,
                        metavar="OPT=VALUE",
                        help="Define chroot environment variables")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Main function.  Create a mock config containing yum repositories
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    yum_repos = load_yum_repos(args.repo_config_list)

    # load the reference config
    reference = os.path.join(args.configdir, args.root + '.cfg')
    config_opts = load_mock_reference(reference)
    if args.config_opt:
        config_opts.update(args.config_opt)
    if args.environment:
        if 'environment' not in config_opts:
            config_opts['environment'] = {}
        config_opts['environment'].update(args.environment)
    conf_key = 'dnf.conf' if 'dnf.conf' in config_opts else 'yum.conf'
    mock_config_fp = StringIO.StringIO(config_opts[conf_key])
    mock_repos = ConfigParser.SafeConfigParser()
    mock_repos.readfp(mock_config_fp)

    # replace repo sections in the mock config
    update_mock_repos(mock_repos, yum_repos, args.yum_config_opt)
    mock_config_fp.truncate(0)
    mock_repos.write(mock_config_fp)
    config_opts[conf_key] = mock_config_fp.getvalue()

    # write new config
    with open(args.mockconfig, "w") as fileh:
        write_mock_cfg(fileh, config_opts)
