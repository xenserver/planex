"""
python-setuptools definition for planex
"""

from setuptools import setup

setup(name='planex',
      version='4.0.0-beta2',
      packages=['planex', 'planex.cmd'],
      package_data={'planex': ['Makefile.rules']},
      entry_points={
          'console_scripts': [
              'planex-build-mock = planex.cmd.mock:main',
              'planex-clone= planex.cmd.clone:main',
              'planex-create-mock-config = planex.cmd.createmockconfig:main',
              'planex-depend = planex.cmd.depend:main',
              'planex-fetch = planex.cmd.fetch:main',
              'planex-init = planex.cmd.init:main',
              'planex-make-srpm = planex.cmd.makesrpm:main',
              'planex-manifest = planex.cmd.manifest:main',
              'planex-pin = planex.cmd.pin:main'
          ]
      })
