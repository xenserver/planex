"""
python-setuptools definition for planex
"""

from setuptools import setup

setup(name='planex',
      version='0.8.0',
      packages=['planex'],
      include_package_data=True,
      package_data={'planex': ['Makefile.rules']},
      entry_points={
          'console_scripts': [
              'planex-init = planex.init:_main',
              'planex-cache = planex.cache:_main',
              'planex-fetch = planex.fetch:_main',
              'planex-pin = planex.pin:_main',
              'planex-depend = planex.depend:main',
              'planex-make-srpm = planex.makesrpm:_main'
          ]
      })
