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
    if os.path.exists(args.pins_dir):
        if not os.path.isdir(args.pins_dir):
            raise Exception(
                "Output directory exists and is not a directory: '%s'" %
                args.pins_dir)
    else:
        os.makedirs(args.pins_dir)

    pins = parse_pins_file(args)
    for (spec, pin_target) in pins.iteritems():
        # we're assuming for now that the target is a git repository
        repo, _, treeish = pin_target.partition('#')
        pin_version = describe(repo, treeish) if treeish else describe(repo)

        tmpdir = tempfile.mkdtemp(prefix='planex-pin')
        tmp_archive = archive(repo, treeish, pin_version, tmpdir)
        tar_path = os.path.join(args.pins_dir, os.path.basename(tmp_archive))
        maybe_copy(tmp_archive, tar_path, args.force)
        shutil.rmtree(tmpdir)

        out_spec_path = os.path.join(args.pins_dir, os.path.basename(spec))
        tmp_spec = tempfile.NamedTemporaryFile(mode='w+', prefix='planex-pin',
                                               delete=False)
        tmp_spec.write(pinned_spec_of_spec(spec, pin_version, tar_path))
        tmp_spec.close()
        maybe_copy(tmp_spec.name, out_spec_path, args.force)
        os.remove(tmp_spec.name)


def parse_pins_file(args):
    pins = {}
    if os.access(args.pins_file, os.R_OK):
        with open(args.pins_file, 'r') as pins_file:
            for line in pins_file.readlines():
                if re.match(r'^\s*#', line):
                    continue
                (spec, pin) = line.split(' ', 1)
                pins[spec] = pin.strip()
    return pins


def serialise_pins(pins, path):
    lines = []
    for (spec, target) in pins.iteritems():
        lines.append("%s %s\n" % (spec, target))
    with open(path, 'w+') as pins_file:
        pins_file.writelines(lines)


def list_pins(args):
    pins = parse_pins_file(args)
    for (spec, pin) in pins.iteritems():
        print "* %s -> %s" % (spec, pin)


def add_pin(args):
    if not os.access(args.spec_file, os.R_OK):
        sys.stderr.write("error: File does not exist: '%s'\n" % args.spec_file)
        sys.exit(1)
    pins = parse_pins_file(args)
    normalised_path = os.path.relpath(args.spec_file)
    if normalised_path in pins:
        sys.stdout.write("error: Package is already pinned:\n* %s -> %s\n" %
                         (normalised_path, pins[normalised_path]))
        sys.exit(1)
    pins[normalised_path] = args.target
    serialise_pins(pins, args.pins_file)


def remove_pin(args):
    pins = parse_pins_file(args)
    normalised_path = os.path.relpath(args.spec_file)
    if normalised_path in pins:
        del pins[os.path.relpath(args.spec_file)]
        serialise_pins(pins, args.pins_file)
        pin_spec_path = os.path.join(args.pins_dir,
                                     os.path.basename(args.spec_file))
        os.remove(pin_spec_path)
        os.utime(args.spec_file, None)


def print_rules(args):
    pins = parse_pins_file(args)
    for (spec, pin) in pins.iteritems():
        pinned_spec_path = os.path.join(args.pins_dir, os.path.basename(spec))
        repo, _, _ = pin.partition('#')
        dependencies = "$(wildcard %s) %s" % (os.path.join(repo, ".git/**/*"),
                                              args.pins_file)
        print "deps: %s" % pinned_spec_path
        print "%s: %s" % (pinned_spec_path, dependencies)
        print "\tplanex-pin --pins-file {0} --pins-dir {1} update".format(
            args.pins_file, args.pins_dir)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    # top-level parser
    parser = argparse.ArgumentParser(
        description='Pin a package to a specific version')
    parser.add_argument('--verbose', '-v', help='Be verbose',
                        action='store_true')
    parser.add_argument('--pins-file', default='pins',
                        help='Pins file (default: pins)')
    parser.add_argument('--pins-dir', default='PINS',
                        help='Directory of pin artifcats (default: PINS)')
    subparsers = parser.add_subparsers(title='COMMANDS')
    # parser for the 'update' command
    parser_update = subparsers.add_parser('update', help='Refresh a given pin')
    parser_update.add_argument('--force', '-f', action='store_true',
                               help="Don't copy archive if unchanged")
    parser_update.set_defaults(func=update)
    # parser for the 'list' command
    parser_list = subparsers.add_parser('list', help='List active pins')
    parser_list.set_defaults(func=list_pins)
    # parser for the 'add' command
    parser_add = subparsers.add_parser('add', help='Add a new pin definition')
    parser_add.add_argument('spec_file', help='Spec file to pin')
    parser_add.add_argument('target',
                            help='Pin target: <path-to-git-repo>#<tree-ish>')
    parser_add.set_defaults(func=add_pin)
    # parser for the 'remove' command
    parser_remove = subparsers.add_parser('remove', help='Remove a pin')
    parser_remove.add_argument('spec_file', help='Spec file to un-pin')
    parser_remove.set_defaults(func=remove_pin)
    # parser for the 'rules' command
    parser_rules = subparsers.add_parser('rules', help='Pint pin make rules')
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
