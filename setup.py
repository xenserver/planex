"""
python-setuptools definition for planex
"""

import os
from setuptools import setup


def read_version():
    """Extract the version number from the version file."""
    setup_py_path = os.path.dirname(os.path.realpath(__file__))
    version_file = os.path.join(setup_py_path, 'config', 'version')
    with open(version_file, 'r') as handle:
        ver = handle.read().replace('\n', '')
    return ver


setup(name='planex',
      version=read_version(),
      url='https://github.com/xenserver/planex',
      maintainer='Simon Rowe',
      maintainer_email='simon.rowe@citrix.com',

      license='LGPL 2.1',

      packages=['planex', 'planex.cmd'],
      package_data={'planex': ['Makefile.rules']},
      entry_points={
          'console_scripts': [
              'planex-build-mock = planex.cmd.mock:main',
              'planex-clone = planex.cmd.clone:main',
              'planex-create-mock-config = planex.cmd.createmockconfig:main',
              'planex-depend = planex.cmd.depend:main',
              'planex-fetch = planex.cmd.fetch:main',
              'planex-init = planex.cmd.init:main',
              'planex-make-srpm = planex.cmd.makesrpm:main',
              'planex-pin = planex.cmd.pin:main'
          ]
      },
      install_requires=[
          'argcomplete',
          'argparse',
          'gitpython',
          'pathlib2',
          'requests'
      ],
      python_requires='==2.7.*')
