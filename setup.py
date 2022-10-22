import os
import pkg_resources
from setuptools import setup, find_packages

setup(
    name="maestro_worker_python",
    py_modules=["maestro_worker_python"],
    version="1.0.1",
    description="Utility to run workers on Moises/Maestro",
    readme="README.md",
    python_requires=">=3.8",
    author="Moises.ai",
    url="https://github.com/moises-ai/maestro-worker-python",
    license="MIT",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        str(r)
        for r in pkg_resources.parse_requirements(
            open(os.path.join(os.path.dirname(__file__), "requirements.txt"))
        )
    ],
    entry_points = {
        'console_scripts': ['maestro-server=maestro_worker_python.server:main', 'maestro-cli=maestro_worker_python.cli:main', 'maestro-init=maestro_worker_python.init:main'],
        
    },
    include_package_data=True,
    extras_require={'dev': ['pytest']},
)