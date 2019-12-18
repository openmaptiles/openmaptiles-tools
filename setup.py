import setuptools
import re
from pathlib import Path

path = Path('.')

with (path / "README.md").open() as fh:
    long_description = fh.read()

version_file = path / "openmaptiles" / "__init__.py"
with version_file.open() as fh:
    m = re.search(r"^__version__\s*=\s*(['\"])([^'\"]*)\1", fh.read().strip(), re.M)
    if not m:
        raise ValueError(f"Version string is not found in {version_file}")
    version = m.group(2)

with (path / "requirements.txt").open(encoding="utf-8") as fh:
    # Requirements will contain a list of libraries without version restrictions
    # It seems this is a common practice for the setup.py vs requirements.txt
    requirements = [m.group(1) for m in
                    (re.match(r'^[ \t]*([^>=<!#\n]+).*', l) for l in fh.readlines())
                    if m]

scripts = [str(p) for p in path.glob('bin/*') if p.is_file()]

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
    scripts=scripts,
    install_requires=requirements,
)
