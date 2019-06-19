"""
planex-clone: Checkout sources referred to by a pin file
"""
from __future__ import print_function

import argparse
import json
import logging
from os import getcwd, rename, walk
from os.path import abspath, exists, join, relpath
import re
from string import Template
import shutil
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


SUPPORTED_URL_SCHEMES = ["http", "https"]


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
    # *.pin gets passed down
    # and wildcard expansion has not occured
    if "*" in package:
        print("No pin files found")
        sys.exit(0)

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
         changelog: true,
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
    json_dict[package] = {'URL': url, 'commitish': commitish,
                          'watching': 'true'}
    with open(filename, "w") as clone_sources:
        clone_sources.write(json.dumps(json_dict, indent=2, sort_keys=True,
                                       separators=(',', ': ')))
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
    if destination.exists():
        # Take a fresh clone if we are re-cloning
        shutil.rmtree(str(destination))

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


def find_all_files(path):
    """
    Find all the files in a path (excluding .git contents)
    Git repo.untracked will skip ignores (which we need to
    add on first expansion of a tarball)
    """
    results = []
    for root, _, files in walk(path):
        if '.git' in root:
            continue
        results.extend([abspath(join(root, filename)) for filename in files])

    return results


def extract(url_str, destination):
    """
    Fetch a non-git resource and create a git repository
    """
    archive_file = None
    # pylint: disable=no-member
    destination.mkdir(parents=True, exist_ok=True)
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
    if tarfile.is_tarfile(archive_path):
        logging.info("Fetch and extract %s into %s", url_str, destination)
        with tarfile.open(archive_path) as tara:
            tara.extractall(str(destination))
        index = repo.index
        index.add(find_all_files(str(destination)))
        index.commit("Repo generated by planex-clone")

    if archive_file:
        # delete temp file
        archive_file.close()

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


def clone_with_patchq(repos, base_dest, base_res, pq_res):
    """
    Given a source and patchqueue resource clone repos and apply the patchqueue
    """
    base_repo = clone_resource(base_res, base_dest)

    pq_dest = Path(repos, re.sub(r'\.git$', '', pq_res.basename))
    pq_repo = clone_resource(pq_res, pq_dest)
    apply_patchqueue(base_repo, pq_repo, pq_res.prefix)


def archive_resource(resource, destination):
    """
    Write an archive of a resource
    """
    archive_path = Path(destination, resource.basename)
    if resource.is_repo:
        temp_dir = tempfile.mkdtemp(prefix='clone-')
        try:
            repo = clone(resource.url, temp_dir, resource.commitish)
            logging.debug("Archiving %s@%s to %s", resource.url,
                          resource.commitish, archive_path)
            with archive_path.open("wb") as output:
                repo.archive(output, treeish=str(resource.commitish),
                             prefix=resource.prefix)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        url = urlparse(resource.url)
        if url.scheme in SUPPORTED_URL_SCHEMES:
            logging.debug("Fetching %s to %s", resource.url, archive_path)
            fetch_url(url, str(archive_path), 5)
        elif url.scheme in ['', 'file'] and url.netloc == '':
            logging.debug("Copying %s to %s", url.path, archive_path)
            shutil.copyfile(url.path, str(archive_path))
    # else: UnsupportedScheme

    return archive_path


def unpack_patches(tarball, destination):
    """
    Extract contents of patches archive
    """
    logging.debug("Unpacking %s to %s", tarball, destination)
    tara = tarfile.open(str(tarball))
    try:
        tara.extractall(str(destination))
    finally:
        tara.close()


def create_repo_from_spec(spec_path, top_path, repo_path):
    """
    Invoke the prep phase of rpmbuild to generate a source directory then
    create a git repo from it
    """
    top_dir = top_path.resolve()
    cmd = ['rpmbuild', '-bp', '--nodeps',
           '--define', '_topdir '+str(top_dir), str(spec_path)]
    logging.debug("Running %s", ' '.join(cmd))
    subprocess.check_call(cmd)

    # move the created build directory under the repo directory
    build_path = list(Path(top_path, 'BUILD').glob('*'))[0]
    rename(str(build_path), str(repo_path))

    git_dir = Path(repo_path, '.git')
    if git_dir.exists():
        # setup already created a git repo
        repo = git.Repo(str(repo_path))
    else:
        repo = git.Repo.init(str(repo_path))
        index = repo.index
        index.add(repo.untracked_files)
        index.commit("Repo generated by planex-clone")

    return repo


def clone_with_patches(spec_path, base_dest, base_res, patches_res, pq_res):
    """
    Given a source, archive and optional patchqueue resource clone repos, apply
    the patches followed by the patchqueue
    """
    work_path = Path(tempfile.mkdtemp(prefix='clone-',
                                      dir=str(base_dest.parent)))
    source_path = Path(work_path, "SOURCES")
    source_path.mkdir(parents=True)

    try:
        archive_resource(base_res, source_path)
        patches_tarball = archive_resource(patches_res, source_path)
        unpack_patches(patches_tarball, work_path)
        base_repo = create_repo_from_spec(spec_path, work_path, base_dest)

        if pq_res:
            pq_dest = Path(str(base_dest)+'.pg')
            pq_repo = clone_resource(pq_res, pq_dest)
            apply_patchqueue(base_repo, pq_repo, pq_res.prefix)

    finally:
        shutil.rmtree(str(work_path), ignore_errors=True)


def get_non_repo_name(source, package):
    """
    Attempt to extract git repository name from archive URL.

    Fallback to package name if no format match found.
    """
    match = re.match(r'.*repos/([^/]*)/archive\?', source)

    if match:
        return match.group(1)

    return package


# pylint: disable=too-many-branches
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
            src_res = resources['Source0']
            if src_res.is_repo:
                # remove trailing '.git'
                repo_path = Path(args.repos,
                                 src_res.basename.rsplit(".git")[0])
            else:
                repo_path = Path(args.repos,
                                 get_non_repo_name(src_res.url, package))
            if not repo_path.parent.exists():
                repo_path.parent.mkdir(parents=True)

            if "PatchQueue0" in resources:
                if "Archive0" in resources:
                    # component with patches and patchqueue
                    clone_with_patches(spec_path, repo_path,
                                       resources['Source0'],
                                       resources['Archive0'],
                                       resources['PatchQueue0'])
                else:
                    # component with patchqueue
                    clone_with_patchq(args.repos, repo_path,
                                      resources['Source0'],
                                      resources['PatchQueue0'])
            elif "Archive0" in resources:
                # component with patches
                clone_with_patches(spec_path, repo_path, resources['Source0'],
                                   resources['Archive0'], None)
            else:
                # clone all fetchable resources
                clone_all_fetchable(args, package, spec)
