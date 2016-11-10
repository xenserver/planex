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
              'planex-build-mock = planex.mock:_main',
              'planex-cache = planex.cache:_main',
              'planex-clone-sources = planex.clonesources:_main',
              'planex-depend = planex.depend:main',
              'planex-extract = planex.extract:_main',
              'planex-fetch = planex.fetch:_main',
              'planex-init = planex.init:_main',
              'planex-make-srpm = planex.makesrpm:_main',
              'planex-manifest = planex.manifest:main',
              'planex-pin = planex.pin:_main'
          ]
      })
