"""
planex-clone: Checkout sources referred to by a pin file
"""
from __future__ import print_function

import argparse
import json
import logging
from os import getcwd
from os.path import exists, join, relpath
from string import Template
import subprocess
import sys
import tempfile
import tarfile

import git

# pylint: disable=relative-import
from six.moves.urllib.parse import urlparse, urlunparse, parse_qs, urlencode

try:
    from pathlib2 import Path
except ImportError:
    from pathlib import Path

from planex.cmd.args import common_base_parser
from planex.cmd.fetch import fetch_url
from planex.config import Configuration
from planex.link import Link
from planex.util import setup_logging
import planex.spec


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Clone package sources',
        parents=[common_base_parser()])
    parser.add_argument("--jenkins", action="store_true",
                        help="Print Jenkinsfile fragment")
    parser.add_argument("--clone", action="store_true",
                        help="Only clone repositories, do not apply patches")
    parser.add_argument("--output", "-o",
                        default=join(getcwd(), "clone_sources.json"),
                        help="Choose output name for clone sources JSON file")
    parser.add_argument("-r", "--repos", metavar="DIR", default="repos",
                        help='Local path to the repositories')
    parser.add_argument("pins", metavar="PINS", nargs="*", help="pin file")
    parser.add_argument("--credentials", metavar="CREDS", default=None,
                        help="Credentials")
    return parser.parse_args(argv)


def find_link_pin(package):
    """
    From a package name locate the link or pin file
    """
    pin_search = Configuration.get('pin', 'search-path',
                                   default='SPECS').split(':')
    for suffix in ('.pin', '.lnk'):
        for subdir in pin_search:
            path = Path(subdir, package+suffix)
            if path.exists():
                return path
    return None


def find_spec(package):
    """
    From a package name locate the spec file
    """
    spec_search = Configuration.get('spec', 'search-path',
                                    default='SPECS').split(':')
    for subdir in spec_search:
        path = Path(subdir, package+'.spec')
        if path.exists():
            return path
    return None


def definitions_for(package):
    """
    Return the package name and paths for link/pin and spec files
    """
    if package.endswith('.pin') or package.endswith('.lnk'):
        # link/pin pathname
        link_pin = Path(package)
        package = link_pin.stem
    else:
        # package name
        link_pin = find_link_pin(package)

    spec = find_spec(package)
    if spec is None:
        sys.exit("No spec file for "+package)

    return package, spec, link_pin


CHECKOUT_TEMPLATE = Template("""checkout poll: true,
         scm: [$$class: 'GitSCM',
               branches: [[name: '$branch']],
               extensions: [[$$class: 'RelativeTargetDirectory',
                             relativeTargetDir: '$checkoutdir'],
                            [$$class: 'LocalBranch']],
               userRemoteConfigs: [
                 [credentialsId: '$credentials',
                  url: '$url']]]
""")


def clone_jenkins_json(package, filename, url, commitish):
    """
    Print JSON file containing repositories to clone
    """
    json_dict = {}
    if exists(filename):
        with open(filename, "r") as clone_sources:
            json_dict.update(json.load(clone_sources))
    json_dict[package] = {'URL': url, 'commitish': commitish}
    with open(filename, "w") as clone_sources:
        clone_sources.write(json.dumps(json_dict, indent=2, sort_keys=True))
        print(file=clone_sources)


def clone_jenkins_groovy(package, destination, credentials, url, commitish):
    """
    Output Groovy SCM fragment for backwards compatibility
    """
    destination = join(destination, package)
    print(CHECKOUT_TEMPLATE.substitute(url=url,
                                       branch=commitish,
                                       checkoutdir=destination,
                                       credentials=credentials))


def clone(url, destination, commitish):
    """
    Clone git repository and checkout at commitish
    """

    if not destination.parent.exists():
        destination.parent.mkdir(parents=True)

    repo = git.Repo.clone_from(url, str(destination))
    if commitish in repo.remotes['origin'].refs:
        branch_name = commitish
        commit = repo.remotes['origin'].refs[commitish]

    elif commitish in repo.tags:
        branch_name = "planex/%s" % commitish
        commit = repo.refs[commitish]

    else:
        branch_name = "planex/%s" % commitish[:8]
        commit = repo.rev_parse(commitish)

    local_branch = repo.create_head(branch_name, commit)
    local_branch.checkout()

    return repo


def extract(url_str, destination):
    """
    Fetch a non-git resource and create a git repository
    """
    archive_file = None

    # pylint: disable=no-member
    destination.mkdir(parents=True)
    repo = git.Repo.init(str(destination))

    logging.debug("Extracting %s to new git repo", url_str)
    url = urlparse(url_str)
    if url.scheme in ('', 'file') and url.netloc == '':
        # local file
        archive_path = url.path
    else:
        # remote URL
        archive_file = tempfile.NamedTemporaryFile(prefix='clone-')
        archive_path = archive_file.name

        query = parse_qs(url.query)
        if 'prefix' in query:
            # strip off the directory prefix
            del query['prefix']
            query_str = urlencode(query, doseq=True)
            url_str = urlunparse((url.scheme, url.netloc, url.path, url.params,
                                  query_str, url.fragment))
            url = urlparse(url_str)

        fetch_url(url, archive_path, 5)

    # extract the archive
    tara = tarfile.open(archive_path)
    tara.extractall(str(destination))
    tara.close()

    if archive_file:
        # delete temp file
        archive_file.close()

    index = repo.index
    index.add(repo.untracked_files)
    index.commit("Repo generated by planex-clone")

    return repo


def clone_resource(resource, destination):
    """
    Clone a resource as a git repository
    """
    if resource.is_repo:
        logging.info("Clone and checkout %s@%s into %s", resource.url,
                     resource.commitish, destination)
        repo = clone(resource.url, destination, resource.commitish)
    else:
        logging.info("Fetch and extract %s into %s", resource.url, destination)
        repo = extract(resource.url, destination)

    return repo


def clone_jenkins(args, spec):
    """
    Generate either a JSON object or a Groovy fragment that describes
    the git-based resources of a package
    """
    for resource in spec.resources():
        if resource.is_repo:
            package = resource.basename.rsplit(".git")[0]
            url = resource.url
            commitish = resource.commitish

            if args.credentials:
                # output Groovy fragment
                print('echo "Cloning %s#%s"' % (url, commitish))
                clone_jenkins_groovy(package, args.repos, args.credentials,
                                     url, commitish)
            else:
                # output JSON object
                clone_jenkins_json(package, args.output, url, commitish)


def clone_all_git(args, spec):
    """
    Clone all git repositories for a package
    """
    for resource in spec.resources():
        if resource.is_repo:
            # remove trailing '.git'
            destination = Path(args.repos, resource.basename[:-4])
            clone_resource(resource, destination)


def clone_all_fetchable(args, package, spec):
    """
    Clone all remote resources for a package
    """
    for resource in spec.resources():
        if resource.is_fetchable:
            if resource.is_repo:
                # remove trailing '.git'
                destination = Path(args.repos, resource.basename[:-4])
            else:
                destination = Path(args.repos, package)
            clone_resource(resource, destination)


def apply_patchqueue(base_repo, pq_repo, prefix):
    """
    Link and then apply a patchqueue repository to a source repository
    """
    status_path = Path(pq_repo.working_dir, prefix, 'status')
    patches_link = Path(base_repo.git_dir, 'patches',
                        base_repo.active_branch.name)

    # make the directory tree for the patches within the base repo
    # pylint: disable=no-member
    patches_link.parent.mkdir(parents=True)

    # link the patchqueue directory for the base repo branch
    rel_path = relpath(str(status_path.parent), str(patches_link.parent))
    patches_link.symlink_to(rel_path)

    # create an empty status file
    with status_path.open('w'):
        pass

    patches = subprocess.check_output(['guilt', 'series'],
                                      cwd=base_repo.working_dir)
    if patches:
        subprocess.check_call(['guilt', 'push', '--all'],
                              cwd=base_repo.working_dir)


def clone_with_patchq(package, repos_base, base_res, pq_res):
    """
    Given a source and patchqueue resource clone repos and apply the patchqueue
    """
    if base_res.is_repo:
        # remove trailing '.git'
        base_dest = Path(repos_base, base_res.basename.rsplit(".git")[0])
    else:
        base_dest = Path(repos_base, package)
    base_repo = clone_resource(base_res, base_dest)

    pq_dest = Path(str(base_dest)+'.pg')
    pq_repo = clone_resource(pq_res, pq_dest)
    apply_patchqueue(base_repo, pq_repo, pq_res.prefix)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)
    setup_logging(args)

    for pin in args.pins:
        package, spec_path, link_pin_path = definitions_for(pin)

        link_pin = None
        if link_pin_path:
            logging.debug("Reading link/pin file %s", link_pin_path)
            link_pin = Link(str(link_pin_path))
        logging.debug("Reading spec file %s", spec_path)
        spec = planex.spec.load(str(spec_path), link=link_pin,
                                check_package_name=False)

        if args.clone:
            # just clone git resources
            clone_all_git(args, spec)
        elif args.jenkins:
            # generate Jenkins information
            clone_jenkins(args, spec)
        else:
            resources = spec.resources_dict()
            if "PatchQueue0" in resources:
                if "Archive0" in resources:
                    raise NotImplementedError("Cloning patched "
                                              "components not implemented")
                else:
                    # component with patchqueue
                    clone_with_patchq(package, args.repos,
                                      resources['Source0'],
                                      resources['PatchQueue0'])
            else:
                # clone all fetchable resources
                clone_all_fetchable(args, package, spec)
