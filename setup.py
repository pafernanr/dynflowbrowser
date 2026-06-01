import os
import setuptools


def read(fname):
    return open(
        os.path.join(os.path.dirname(__file__), fname), encoding="utf-8"
        ).read()


setuptools.setup(
    name='dynflowbrowser',
    version='0.0.0',
    setup_requires=['Jinja2', 'pytz', 'textual', 'pandas'],
    scripts=[
        'dynflowbrowser/bin/__init__.py',
        'dynflowbrowser_export_tasks/bin/__init__.py'],
    entry_points={
        'console_scripts': [
            'dynflowbrowser=dynflowbrowser.bin:main',
            'dynflowbrowser-export-tasks=dynflowbrowser_export_tasks.bin:main',
            ],
        },
    packages=setuptools.find_packages(),
    package_data={
        'dynflowbrowser': ['__VERSION__'],
        'dynflowbrowser.html.css': ['*'],
        'dynflowbrowser.html.js': ['*'],
        'dynflowbrowser.templates': ['*'],
    },
    license='GPLv3',
    author='Pablo Fernández Rodríguez',
    url='https://github.com/pafernanr/dynflowbrowser',
    keywords='theforeman dynflow',
    description="""
        Interactive browser for analyzing Dynflow task execution data from TheForeman/Red Hat Satellite sosreports.""",
    long_description_content_type='text/markdown',
    long_description=read("README.md"),
    classifiers=[
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    )
