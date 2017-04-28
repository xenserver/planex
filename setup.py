"""
python-setuptools definition for planex
"""

from setuptools import setup

setup(name='planex',
      version='0.22.0',
      packages=['planex', 'planex.cmd'],
      include_package_data=True,
      package_data={'planex': ['Makefile.rules']},
      entry_points={
          'console_scripts': [
              'planex-build-mock = planex.cmd.mock:main',
              'planex-clone= planex.cmd.clone:main',
              'planex-create-mock-config = planex.cmd.createmockconfig:main',
              'planex-depend = planex.cmd.depend:main',
              'planex-whatchanged = planex.cmd.whatchanged:main',
              'planex-extract = planex.cmd.extract:main',
              'planex-fetch = planex.cmd.fetch:main',
              'planex-init = planex.cmd.init:main',
              'planex-make-srpm = planex.cmd.makesrpm:main',
              'planex-manifest = planex.cmd.manifest:main',
              'planex-patchqueue = planex.cmd.patchqueue:main'
          ]
      })
