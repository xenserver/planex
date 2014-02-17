from setuptools import setup

setup(name='planex',
      version='0.0.0',
      packages=['planex'],
      entry_points={
          'console_scripts': [
              'planex-configure = planex.configure:main',
              'planex-build = planex.build:main',
              'planex-install = planex.install:main',
          }
      })
