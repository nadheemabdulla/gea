"""Setup for my_google_drive XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='edx-gea',
    version='0.2.1',
    description='An XBlock to grade external activities',   # TODO: write a better description.
    packages=[
        'edx_gea',
    ],
    install_requires=[
        'XBlock',
        'xblock-utils',
    ],
#    dependency_links=[
#        'http://github.com/edx-solutions/xblock-utils/tarball/master#egg=xblock-utils',
#    ],
    entry_points={
        'xblock.v1': [
            'edx_gea = edx_gea:GradeExternalActivityXBlock'
        ]
    },
    package_data=package_data("edx_gea", ["static", "templates", "public", "locale"]),
)
