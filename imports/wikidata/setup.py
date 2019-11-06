from distutils.core import setup

setup(
    name='import-wikidata',
    version='0.1.0',
    packages=['wikidata'],
    license='MIT',
    scripts=[
        'bin/import-wikidata',
    ],
    install_requires=[
        'psycopg2',
        'sortedcontainers',
    ],
)
