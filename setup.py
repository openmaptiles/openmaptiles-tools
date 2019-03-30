#from distutils.core import setup
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read().strip()

setuptools.setup(
    name='openmaptiles-tools',
    version=version,
    packages=['openmaptiles'],
    description="The OpenMapTiles tools for generating TM2Source projects, imposm3 mappings and SQL instructions from "
                "OpenMapTiles layers. We encourage other people to use this for their vector tile projects as well "
                "since this approach works well for us.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openmaptiles/openmaptiles-tools",
    license='MIT',
    scripts=[
        'bin/generate-doc',
        'bin/generate-diagram-pngs',
        'bin/generate-etlgraph',
        'bin/generate-imposm3',
        'bin/generate-mapping-graph',
        'bin/generate-metadata',
        'bin/generate-sql',
        'bin/generate-sqlquery',
        'bin/generate-tm2source',
        'bin/generate-sqltomvt',
    ],
    # Make sure this list is the same as in the requirements.txt
    install_requires=[
        'docopt',
        'pyyaml',
        'graphviz',
    ],
)
