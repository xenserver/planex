from setuptools import setup

setup(name='planex',
      version='0.0.0',
      py_modules=['planex_globals'],
      entry_points={
          'console_scripts': [
              'planex-configure = planex.configure:main',
              'planex-build = planex.build:main',
              'planex-install = planex.install:main',
          ]
      },
      scripts=['bin/spectool']
      )
