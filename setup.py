"""
python-setuptools definition for planex
"""

from setuptools import setup

setup(name='planex',
      version='0.11.0',
      packages=['planex'],
      include_package_data=True,
      package_data={'planex': ['Makefile.rules']},
      entry_points={
          'console_scripts': [
              'planex-build-mock = planex.mock:main',
              'planex-cache = planex.cache:main',
              'planex-clone-sources = planex.clonesources:main',
              'planex-depend = planex.depend:main',
              'planex-extract = planex.extract:main',
              'planex-fetch = planex.fetch:main',
              'planex-init = planex.init:main',
              'planex-make-srpm = planex.makesrpm:main',
              'planex-manifest = planex.manifest:main',
              'planex-pin = planex.pin:main'
          ]
      })
