"""
planex-clone: Checkout sources referred to by a pin file
"""

from string import Template
import argparse
import os
import subprocess

from planex.link import Link
import planex.util as util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Clone sources')
    parser.add_argument("-P", "--pins-dir", default="PINS",
                        help="Directory containing pin overlays")
    parser.add_argument("--jenkins", action="store_true",
                        help="Print Jenkinsfile fragment")
    parser.add_argument("--credentials", metavar="CREDS", default="",
                        help="Credentials")
    parser.add_argument(
        "-r", "--repos", metavar="DIR", default="repos",
        help='Local path to the repositories')
    parser.add_argument("pins", metavar="PINS", nargs="*", help="pin file")
    return parser.parse_args(argv)


CHECKOUT_TEMPLATE = Template("""checkout poll: true,
         scm:[$$class: 'GitSCM',
              branches: [[name: '$branch']],
              extensions: [[$$class: 'RelativeTargetDirectory',
                            relativeTargetDir: '$checkoutdir'],
                           [$$class: 'LocalBranch']],
              userRemoteConfigs: [
                [credentialsId: '$credentials',
                 url: '$url']]]
""")


def clone(url, destination, branch="master"):
    """Clone repository"""
    cmd = ['git', 'clone', '--branch', branch, url, destination]
    subprocess.check_call(cmd)
    cmd = ['git', 'checkout', '-B', branch]
    subprocess.check_call(cmd, cwd=destination)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)

    for pinpath in args.pins:
        pin = Link(pinpath)
        reponame = os.path.basename(pin.url).rsplit(".git")[0]
        checkoutdir = os.path.join(args.repos, reponame)

        if args.jenkins:
            print 'echo "Cloning %s"' % pin.url
            print CHECKOUT_TEMPLATE.substitute(url=pin.url,
                                               branch=pin.commitish,
                                               checkoutdir=checkoutdir,
                                               credentials=args.credentials)

        else:
            if pin.base:
                base_reponame = os.path.basename(pin.base).rsplit(".git")[0]
                base_checkoutdir = os.path.join(args.repos, base_reponame)
                print "Cloning %s" % pin.base
                util.makedirs(os.path.dirname(base_checkoutdir))
                clone(pin.base, base_checkoutdir, pin.base_commitish)

                print "Cloning %s" % pin.url
                reponame = os.path.basename(pin.url).rsplit(".git")[0]
                checkoutdir = os.path.join(args.repos, reponame)
                clone(pin.url, checkoutdir, pin.commitish)

                # Symlink the patchqueue
                patch_path = os.path.join(base_checkoutdir, ".git/patches")
                util.makedirs(patch_path)

                link_path = os.path.relpath(checkoutdir, patch_path)

                os.symlink(os.path.join(link_path, pin.patchqueue),
                           os.path.join(patch_path, pin.base_commitish))

                # Create empty guilt status for the branch
                status = os.path.join(patch_path, pin.base_commitish, 'status')
                fileh = open(status, 'w')
                fileh.close()

                subprocess.check_call(['guilt', 'push', '--all'],
                                      cwd=base_checkoutdir)

            else:
                print "Cloning %s" % pin.url
                util.makedirs(os.path.dirname(checkoutdir))
                clone(pin.url, checkoutdir, pin.commitish)


if __name__ == "__main__":
    main()
