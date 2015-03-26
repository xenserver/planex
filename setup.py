from setuptools import setup

setup(name='planex',
      version='0.6.0',
      packages=['planex'],
      include_package_data=True,
      package_data={'planex': ['Makefile.rules']},
      data_files=[('/usr/share/planex', ['planex/Makefile.rules']),
                  ('/etc/bash_completion.d/', ['planex/planex.bash'])],
      entry_points={
          'console_scripts': [
              'planex-init = planex.init:main',
              'planex-cache = planex.cache:_main',
              'planex-fetch = planex.fetch:_main',
              'planex-pin = planex.pin:_main',
              'planex-makedeb = planex.makedeb:main',
              'planex-depend = planex.depend:main'
          ]
      })
