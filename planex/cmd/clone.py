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


CHECKOUT_TEMPLATE = Template("""check ut poll: true,
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
            print "Cloning %s" % pin.url
            util.makedirs(os.path.dirname(checkoutdir))
            clone(pin.url, checkoutdir, pin.commitish)

if __name__ == "__main__":
    main()
