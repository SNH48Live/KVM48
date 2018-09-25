#!/usr/bin/env python3

import pathlib

import setuptools


HERE = pathlib.Path(__file__).resolve().parent
with open(HERE.joinpath('src/kvm48/version.py').as_posix()) as fp:
    exec(fp.read())

setuptools.setup(
    name='KVM48',
    version=__version__,
    description='Koudai48 VOD Manager',
    long_description='See https://github.com/SNH48Live/KVM48#readme.',
    url='https://github.com/SNH48Live/KVM48',
    author='Zhiming Wang',
    author_email='pypi@snh48live.org',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
    ],
    keywords='48 snh48 koudai48 pocket48',
    package_dir={'': 'src'},
    packages=['kvm48'],
    install_requires=['PyYAML', 'arrow', 'attrdict', 'requests'],
    entry_points={
        'console_scripts': [
            'kvm48=kvm48.kvm48:main',
        ],
    },
)
