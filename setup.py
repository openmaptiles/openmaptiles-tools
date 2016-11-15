from distutils.core import setup

setup(
    name='openmaptiles-tools',
    version='0.1',
    packages=['openmaptiles'],
    license='MIT',
    long_description=open('README.md').read(),
    scripts=[
        'bin/generate-tm2source',
        'bin/generate-imposm3',
        'bin/generate-sql',
        'bin/generate-doc',
        'bin/generate-etlgraph',       
    ],
    install_requires=[
      'docopt',
      'pyyaml',
      'graphviz',
    ],
)
