from distutils.core import setup

setup(
    name='openmaptiles-tools',
    version=open('VERSION').read(),
    packages=['openmaptiles'],
    license='MIT',
    long_description=open('README.md').read(),
    scripts=[
        'bin/generate-doc',
        'bin/generate-etlgraph',       
        'bin/generate-imposm3',
        'bin/generate-mapping-graph',       
        'bin/generate-metadata',        
        'bin/generate-sql',
        'bin/generate-sqlquery',        
        'bin/generate-tm2source',
    ],
    install_requires=[
      'docopt',
      'pyyaml',
      'graphviz',
    ],
)
