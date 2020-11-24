#!/usr/bin/env python

import sys
import distutils.core

from pip.download import PipSession
from pip.req import parse_requirements

from lifeloopweb import __version__

try:
    import setuptools
except ImportError:
    pass


def requires(path):
    return [str(r.req) for r in parse_requirements(path, session=PipSession())
            if r]


distutils.core.setup(
    name="lifeloopweb",
    version=__version__,
    packages=["lifeloopweb"],
    package_data={
        "lifeloopweb": [],
        },
    author="LifeLoop.Live",
    author_email="info@lifeloop.live",
    url="https://lifeloop.live",
    download_url="https://github.com/toneosa/lifeloopweb/releases",
    license="https://github.com/toneosa/lifeloopweb/blob/master/LICENSE",
    description="",
    install_requires=requires("requirements.txt"),
    entry_points={
        "console_scripts": [
            "lifeloop_shell = lifeloopweb.shell:main",
            "lifeloop_flask_server = lifeloopweb.lifeloopweb_app:run_server",
            "lifeloop_gunicorn_server = lifeloopweb.wsgi:run_server",
            "lifeloop_db_manage = lifeloopweb.db.migrations.cli:main",
        ]}
    )
