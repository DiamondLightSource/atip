"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""


from setuptools import setup
from os import path
# io.open is needed for projects that support Python 2.7
from io import open

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.mrst'), encoding='utf-8') as f:
    long_desc = f.read()

setup(
    name='atip',

    version='0.0.1',

    description='ATIP: Accelerator Toolbox Interface for Pytac',

    long_description=long_desc,

    url='https://github.com/T-Nicholls/atip',

    author='Tobyn Nicholls',

    author_email='tobyn.nicholls@diamond.ac.uk',

    license='Apache License 2.0',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='accelerator physics',

    packages=['atip'],

    include_package_data=True,

    zip_safe=False,

    install_requires=['pytac, at-python'],
)
