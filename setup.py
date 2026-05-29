import os
import setuptools


version_file = os.path.join(
    os.path.dirname(__file__), 'dynflowbrowser', '__VERSION__'
)


def read(fname):
    return open(
        os.path.join(os.path.dirname(__file__), fname), encoding="utf-8"
        ).read()


setuptools.setup(
    name='dynflowbrowser',
    version=read(version_file),
    install_requires=['Jinja2', 'pandas', 'pytz', 'textual>=0.50.0'],
    setup_requires=['Jinja2', 'pandas', 'pytz', 'textual>=0.50.0'],
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
        'dynflowbrowser.lib.ui.httpd': [
            'templates/*',
            'static/css/*',
            'static/js/*'
        ],
    },
    license='GPLv3',
    author='Pablo Fernández Rodríguez',
    url='https://github.com/pafernanr/dynflowbrowser',
    keywords='theforeman dynflow',
    description="""
        Browse sosreport dynflow data with an interactive terminal UI or
        web interface for tasks, plans, actions and steps.""",
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
