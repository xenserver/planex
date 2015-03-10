"""
planex-pin: Generate a new override spec file for a given package
"""

import argparse
import os
import sys
import re
import logging
from planex.util import run


def describe(repo, treeish="HEAD"):
    dotgitdir = os.path.join(repo, ".git")

    if not os.path.exists(dotgitdir):
        raise Exception("Pin target is not a git repository: '%s'" % repo)

    # First, get the hash of the commit
    cmd = ["git", "--git-dir=%s" % dotgitdir, "rev-parse", treeish]
    sha = run(cmd)['stdout'].strip()

    # Now lets describe that hash
    cmd = ["git", "--git-dir=%s" % dotgitdir, "describe", "--tags", sha]
    description = run(cmd, check=False)['stdout'].strip()

    # if there are no tags, use the number of commits
    if description == "":
        cmd = ["git", "--git-dir=%s" % dotgitdir, "log", "--oneline", sha]
        commits = run(cmd)['stdout'].strip()
        description = str(len(commits.splitlines()))

    # replace '-' with '+' in description to not confuse rpm
    match = re.search("[^0-9]*", description)
    matchlen = len(match.group())
    return description[matchlen:].replace('-', '+')


def archive(repo, commit_hash, pin_version, target_dir):
    dotgitdir = os.path.join(repo, ".git")

    prefix = "%s-%s" % (os.path.basename(repo), pin_version)
    path = os.path.join(target_dir, "%s.tar" % prefix)

    run(["git", "--git-dir=%s" % dotgitdir, "archive", commit_hash,
         "--prefix=%s/" % prefix, "-o", path])
    run(["gzip", "--no-name", "-f", path])

    return path + ".gz"


def pinned_spec_of_spec(spec_path, pin_version, source_path):
    spec_in = open(spec_path)
    spec_contents = spec_in.readlines()
    spec_in.close()

    source_url = "file://" + os.path.abspath(source_path)

    pinned_spec = []
    for line in spec_contents:
        # replace the source url
        match = re.match(r'^([Ss]ource\d*:\s+)(.+)\n', line)
        if match:
            line = match.group(1) + source_url + "\n"
        # replace the version
        match = re.match(r'^([Vv]ersion\d*:\s+)(.+)\n', line)
        if match:
            print "replacing %s with %s" % (match.group(2), pin_version)
            line = match.group(1) + pin_version + "\n"
        pinned_spec.append(line)

    return "".join(pinned_spec)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Pin a package to a specific version')
    parser.add_argument('spec', help='RPM Spec file')
    parser.add_argument('pin', help='Specific version, local path or git url')
    parser.add_argument('output_dir', help='Path to write output spec file')
    parser.add_argument('--remove', '-r', help='Remove pin for this package',
                        action='store_true')
    parser.add_argument('--verbose', '-v', help='Be verbose',
                        action='store_true')
    return parser.parse_args(argv)


def main(argv):
    """
    Main function
    """
    args = parse_args_or_exit(argv)
    if args.verbose:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    if os.path.exists(args.output_dir):
        if not os.path.isdir(args.output_dir):
            raise Exception(
                "Output directory exists and is not a directory: '%s'" %
                args.output_dir)
    else:
        os.makedirs(args.output_dir)

    # we're assuming for now that the target is a git repository
    repo, _, hash = args.pin.partition('#')
    pin_version = describe(repo, hash) if hash else describe(repo)

    source_path = archive(repo, hash, pin_version, args.output_dir)

    spec_filename = os.path.basename(args.spec)
    output_spec_path = os.path.join(args.output_dir, spec_filename)
    with open(output_spec_path, 'w') as f:
        f.write(pinned_spec_of_spec(args.spec, pin_version, source_path))


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
