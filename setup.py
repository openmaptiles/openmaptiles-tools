from distutils.core import setup

setup(
    name='openmaptiles-tools',
    version=open('VERSION').read(),
    packages=['openmaptiles'],
    license='MIT',
    long_description=open('README.md').read(),
    scripts=[
        'bin/generate-tm2source',
        'bin/generate-imposm3',
        'bin/generate-sql',
        'bin/generate-sqlquery',        
        'bin/generate-doc',
        'bin/generate-etlgraph',       
        'bin/generate-mapping-graph',       
    ],
    install_requires=[
      'docopt',
      'pyyaml',
      'graphviz',
    ],
)
