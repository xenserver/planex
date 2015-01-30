from setuptools import setup

setup(name='planex',
      version='0.6.0',
      packages=['planex'],
      include_package_data = True,
      package_data={
	'planex':['Makefile.common']
	},
      data_files=[('/usr/share/planex',['planex/Makefile.common'])],
      entry_points={
          'console_scripts': [
              'planex-configure = planex.configure:_main',
              'planex-build = planex.build:main',
              'planex-clone = planex.clone:main',
              'planex-cache = planex.cache:_main',
              'planex-downloader = planex.downloader:main',
              'planex-makedeb = planex.makedeb:main',
              'planex-depend = planex.depend:main'
          ]
      })
