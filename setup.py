from setuptools import setup

setup(name='planex',
      version='0.5.0',
      packages=['planex'],
      entry_points={
          'console_scripts': [
              'planex-configure = planex.configure:_main',
              'planex-build = planex.build:main',
              'planex-clone = planex.clone:main',
              'planex-cache = planex.cache:_main',
              'planex-downloader = planex.downloader:main',
              'planex-makedeb = planex.makedeb:main',
              'planex-specdep = planex.specdep:main'
          ]
      })
