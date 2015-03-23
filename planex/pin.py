"""
planex-pin: Generate a new override spec file for a given package
"""

import argparse
import os
import sys
import re
import logging
import tempfile
import hashlib
import shutil
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


def hash_of_file(path):
    md5sum = hashlib.md5()
    with open(path, 'r') as in_f:
        md5sum.update(in_f.read())
    return md5sum.digest()


def maybe_copy(src, dst, force=False):
    if force or not (os.path.exists(dst) and
                     hash_of_file(src) == hash_of_file(dst)):
        shutil.copy(src, dst)


def update(args):
    if os.path.exists(args.output_dir):
        if not os.path.isdir(args.output_dir):
            raise Exception(
                "Output directory exists and is not a directory: '%s'" %
                args.output_dir)
    else:
        os.makedirs(args.output_dir)

    pins = parse_pins_file(args)
    for (spec, pin_target) in pins.iteritems():
        # we're assuming for now that the target is a git repository
        repo, _, treeish = pin_target.partition('#')
        pin_version = describe(repo, treeish) if treeish else describe(repo)

        tmpdir = tempfile.mkdtemp(prefix='planex-pin')
        tmp_archive = archive(repo, treeish, pin_version, tmpdir)
        tar_path = os.path.join(args.output_dir, os.path.basename(tmp_archive))
        maybe_copy(tmp_archive, tar_path, args.force)
        shutil.rmtree(tmpdir)

        out_spec_path = os.path.join(args.output_dir, os.path.basename(spec))
        tmp_spec = tempfile.NamedTemporaryFile(mode='w+', prefix='planex-pin',
                                               delete=False)
        tmp_spec.write(pinned_spec_of_spec(spec, pin_version, tar_path))
        tmp_spec.close()
        maybe_copy(tmp_spec.name, out_spec_path, args.force)
        os.remove(tmp_spec.name)


def parse_pins_file(args):
    pins = {}
    for line in args.pins_file.readlines():
        if re.match(r'^\s*#', line):
            continue
        (spec, pin) = line.split(' ', 1)
        pins[spec] = pin.strip()
    return pins


def list_pins(args):
    pins = parse_pins_file(args)
    for (spec, pin) in pins.iteritems():
        print "* %s -> %s" % (spec, pin)


def print_rules(args):
    pins = parse_pins_file(args)
    for (spec, pin) in pins.iteritems():
        pinned_spec_path = os.path.join(args.pins_dir, os.path.basename(spec))
        repo, _, _ = pin.partition('#')
        dependencies = "$(wildcard %s) %s" % (os.path.join(repo, ".git/**/*"),
                                              args.pins_file.name)
        print "deps: %s" % pinned_spec_path
        print "%s: %s" % (pinned_spec_path, dependencies)
        print "\tplanex-pin update %s %s" % (args.pins_file.name,
                                             args.pins_dir)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    # top-level parser
    parser = argparse.ArgumentParser(
        description='Pin a package to a specific version')
    parser.add_argument('--verbose', '-v', help='Be verbose',
                        action='store_true')
    subparsers = parser.add_subparsers(title='COMMANDS')
    # parser for the 'update' command
    parser_update = subparsers.add_parser('update', help='Refresh a given pin')
    parser_update.add_argument('pins_file', type=argparse.FileType('r+'),
                               help='File containing pin list')
    parser_update.add_argument('output_dir', help='To store pinned package')
    parser_update.add_argument('--force', '-f', action='store_true',
                               help="Don't copy archive if unchanged")
    parser_update.set_defaults(func=update)
    # parser for the 'list' command
    parser_list = subparsers.add_parser('list', help='List active pins')
    parser_list.add_argument('pins_file', type=argparse.FileType('r+'),
                             help='File containing pin list')
    parser_list.set_defaults(func=list_pins)
    # parser for the 'rules' command
    parser_rules = subparsers.add_parser('rules', help='Pint pin make rules')
    parser_rules.add_argument('pins_file', type=argparse.FileType('r+'),
                              help='File containing pin list')
    parser_rules.add_argument('pins_dir', help='Directory used with update')
    parser_rules.set_defaults(func=print_rules)

    return parser.parse_args(argv)


def main(argv):
    """
    Main function
    """
    args = parse_args_or_exit(argv)
    if args.verbose:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    args.func(args)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
