from distutils.core import setup

setup(
    name='openmaptiles-tools',
    version='0.5.0',
    packages=['openmaptiles'],
    license='MIT',
    scripts=[
        'bin/generate-doc',
        'bin/generate-etlgraph',
        'bin/generate-imposm3',
        'bin/generate-mapping-graph',
        'bin/generate-metadata',
        'bin/generate-sql',
        'bin/generate-sqlquery',
        'bin/generate-tm2source',
        'bin/replace-layer',
    ],
    install_requires=[
      'docopt',
      'pyyaml',
      'graphviz',
    ],
)
