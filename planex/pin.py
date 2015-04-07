"""
planex-pin: Generate a new override spec file for a given package
"""

import argparse
import argcomplete
import os
import sys
import re
import glob
import logging
import tempfile
import hashlib
import shutil
import json
import rpm
from planex.util import run
from planex.util import setup_sigint_handler
from planex.util import add_common_parser_options
from planex.util import setup_logging


def describe(repo, treeish="HEAD"):
    """
    Return an RPM compatible version string for a git repo at a given commit
    """
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


def archive(repo, commit_hash, prefix, target_dir):
    """
    Archive a git repo at a given commit with a specified version prefix.
    Returns the path to a tar.gz to be used as a source for building an RPM.
    """
    dotgitdir = os.path.join(repo, ".git")

    prefix = "%s-%s" % (os.path.basename(repo), prefix)
    path = os.path.join(target_dir, "%s.tar" % prefix)

    run(["git", "--git-dir=%s" % dotgitdir, "archive", commit_hash,
         "--prefix=%s/" % prefix, "-o", path])
    run(["gzip", "--no-name", "-f", path])

    return path + ".gz"


def pinned_spec_of_spec(spec_path, src_map):
    """
    Given a path to a spec file, and a map of source number to (version, path),
    return the contents of a new spec file for the pinned package. The new spec
    file will have the source paths overriden and the Release tag set to
    a sensible combination of the versions of the source pin targets. This.
    This conforms to the Fedora Project packaging guidelines for what to put
    into the Release Tag (see commit message for relevant link).
    """
    logging.debug("Generating pinned spec for %s from source_map %s",
                  spec_path, src_map)
    spec_in = open(spec_path)
    spec_contents = spec_in.readlines()
    spec_in.close()

    pinned_spec = []
    for line in spec_contents:
        # replace the source url(s)
        for src_num in src_map.iterkeys():
            match = re.match(r'^([Ss]ource%s*:\s+)(.+)\n' % src_num, line)
            if match:
                source_url = "file://" + os.path.abspath(src_map[src_num][1])
                logging.info("Replacing Source%s of %s with %s",
                             src_num, spec_path, src_map[src_num][1])
                line = match.group(1) + source_url + "\n"
        # replace the release
        match = re.match(r'^([Rr]elease:\s+)([^%]+)(.*)\n', line)
        if match:
            # combine the source override versions to get the package release
            release_stamps = ["s{0}+{1}".format(n, v)
                              for (n, (v, _)) in src_map.items()]
            # Note that %% expands to just %...
            pin_release = "%s+%s" % (match.group(2),
                                     "_".join(sorted(release_stamps)))
            logging.info("Replacing Release %s of %s with %s",
                         match.group(2), spec_path, pin_release)
            line = match.group(1) + pin_release + match.group(3) + "\n"
        pinned_spec.append(line)

    return "".join(pinned_spec)


def version_of_spec_file(path):
    """
    Return the version defined in the spec file at path.
    """
    spec = rpm.ts().parseSpec(path)
    return spec.sourceHeader['version']


def hash_of_file(path):
    """
    Return the md5sum of the contents of a file at a given path.
    """
    md5sum = hashlib.md5()
    with open(path, 'r') as in_f:
        md5sum.update(in_f.read())
    return md5sum.digest()


def maybe_copy(src, dst, force=False):
    """
    Copy a file from src to dst only if their contents differ.
    """
    if force or not (os.path.exists(dst) and
                     hash_of_file(src) == hash_of_file(dst)):
        shutil.copy(src, dst)


def update(args):
    """
    Entry point for the 'update' sub-command.
    Refreshes all the pins from the pin definition file, updating the source
    tarball and spec file only if required.
    """
    if os.path.exists(args.pins_dir):
        if not os.path.isdir(args.pins_dir):
            raise Exception(
                "Output directory exists and is not a directory: '%s'" %
                args.pins_dir)
    else:
        os.makedirs(args.pins_dir)

    pins = parse_pins_file(args)
    for (spec, pinned_sources) in pins.iteritems():
        source_map = {}
        orig_version = version_of_spec_file(spec)
        for (src_num, pin_target) in pinned_sources.iteritems():
            # we're assuming for now that the target is a git repository
            repo, _, treeish = pin_target.partition('#')
            src_version = describe(repo, treeish if treeish else None)
            logging.debug("Source%s pin target is at version %s",
                          src_num, src_version)

            tmpdir = tempfile.mkdtemp(prefix='planex-pin')
            tmp_archive = archive(repo, treeish, orig_version, tmpdir)
            tar_name = os.path.basename(tmp_archive).replace(orig_version,
                                                             src_version)
            tar_path = os.path.join(args.pins_dir, tar_name)
            maybe_copy(tmp_archive, tar_path, args.force)
            shutil.rmtree(tmpdir)
            source_map[src_num] = (src_version, tar_path)

        out_spec_path = os.path.join(args.pins_dir, os.path.basename(spec))
        with open(out_spec_path, 'w+') as out_spec_file:
            out_spec_file.write(pinned_spec_of_spec(spec, source_map))


def parse_pins_file(args):
    """
    Return a dictionary of spec files to pin targets from the pin definition
    file.  The file can have comments (lines that begin with a '#') and then
    the pin definitions are a json dump of the dictionary
    """
    lines = []
    if os.access(args.pins_file, os.R_OK):
        with open(args.pins_file, 'r') as pins_file:
            for line in pins_file.readlines():
                if not re.match(r'^\s*#', line):
                    lines.append(line)
    return json.loads(''.join(lines)) if lines else {}


def serialise_pins(pins, path):
    """
    Dump the pin definitions to a file at a given path.
    """
    preamble = [
        "# This file is auto-generated by planex-pin\n",
        "# Do not edit directly, instead use planex-pin {add,list,remove}\n"
    ]
    with open(path, 'w+') as pins_file:
        pins_file.writelines(preamble)
        json.dump(pins, pins_file)


def list_pins(args):
    """
    Entry point for the 'list' sub-command.
    Prints to stdout the pins in the pin definition file.
    """
    pins = parse_pins_file(args)
    for (spec, pinned_sources) in pins.iteritems():
        for (source_number, target) in pinned_sources.iteritems():
            print "* %s : Source%s -> %s" % (spec, source_number, target)


def add_pin(args):
    """
    Entry point for the 'add' sub-command.
    Checks if the spec file exists and add a definition to the pins file.
    """
    if not os.access(args.spec_file, os.R_OK):
        sys.stderr.write("error: File does not exist: '%s'\n" % args.spec_file)
        sys.exit(1)
    pins = parse_pins_file(args)
    normalised_path = os.path.relpath(args.spec_file)
    if normalised_path in pins:
        if args.source in pins[normalised_path] and not args.force:
            sys.exit("error: Package already has source pinned:\n"
                     "* %s : Source%s -> %s\n" %
                     (normalised_path, args.source,
                      pins[normalised_path][args.source]))
        pins[normalised_path].update({args.source: args.target})
    else:
        pins[normalised_path] = {args.source: args.target}
    serialise_pins(pins, args.pins_file)


def remove_pin(args):
    """
    Entry point for the 'remove' sub-command.
    Removes the pin definition from the pins file and touches the original spec
    file to ensure dependencies are regenerated. The next 'rules' command will
    ensure that the override spec file is removed.
    """
    pins = parse_pins_file(args)
    normalised_path = os.path.relpath(args.spec_file)
    if normalised_path in pins:
        if args.source in pins[normalised_path]:
            del pins[normalised_path][args.source]
            if not pins[normalised_path]:
                del pins[normalised_path]
            serialise_pins(pins, args.pins_file)
            os.utime(args.spec_file, None)


def print_rules(args):
    """
    Entry point for the 'rules' sub-command.
    Prints to stdout the Makefile snippet required for pinning updates and
    removes any override spec files for removed pins.
    """
    pins = parse_pins_file(args)
    for (spec, pinned_sources) in pins.iteritems():
        pinned_spec_path = os.path.join(args.pins_dir, os.path.basename(spec))
        repos = [pin.partition('#')[0] for pin in pinned_sources.values()]
        repo_paths = [os.path.abspath(repo) for repo in repos]
        gitdir_paths = [os.path.join(p, ".git/**/*") for p in repo_paths]
        dependencies = "%s %s $(wildcard %s)" % (args.pins_file, spec,
                                                 " ".join(gitdir_paths))
        print "%s: %s" % (args.deps_path, pinned_spec_path)
        print "%s: %s" % (pinned_spec_path, dependencies)
        print "\tplanex-pin --pins-file {0} --pins-dir {1} update".format(
            args.pins_file, args.pins_dir)

    expected_pin_specs = [os.path.join(args.pins_dir, path) for path in pins]
    for pin_spec_path in glob.glob(os.path.join(args.pins_dir, '*.spec')):
        if pin_spec_path not in expected_pin_specs:
            os.remove(pin_spec_path)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    # top-level parser
    parser = argparse.ArgumentParser(
        description='Pin a package to a specific version')
    add_common_parser_options(parser)
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
    parser_add.add_argument('--force', '-f', action='store_true',
                            help='Override any existing pin definition')
    parser_add.add_argument('--source', default="0",
                            help='Which source number to pin. (default: 0)')
    parser_add.add_argument('spec_file', help='Spec file to pin')
    parser_add.add_argument('target',
                            help='Pin target: <path-to-git-repo>#<tree-ish>')
    parser_add.set_defaults(func=add_pin)
    # parser for the 'remove' command
    parser_remove = subparsers.add_parser('remove', help='Remove a pin')
    parser_remove.add_argument('--source', default="0",
                               help='Which source to unpin. (default: 0)')
    parser_remove.add_argument('spec_file', help='Spec file to un-pin')
    parser_remove.set_defaults(func=remove_pin)
    # parser for the 'rules' command
    parser_rules = subparsers.add_parser('rules', help='Print pin make rules')
    parser_rules.add_argument('deps_path', help='Path to deps file')
    parser_rules.set_defaults(func=print_rules)

    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Main function
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)
    args.func(args)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
