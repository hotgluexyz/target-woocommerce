#!/usr/bin/env python

from setuptools import setup

setup(
    name='target-woocommerce',
    version='1.0.1',
    description='hotglue target for exporting data to woocommerce API',
    author='hotglue',
    url='https://hotglue.xyz',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['target_woocommerce'],
    install_requires=[
        'argparse==1.4.0',
        'woocommerce==3.0.0'
    ],
    entry_points='''
        [console_scripts]
        target-woocommerce=target_woocommerce:main
    ''',
    packages=['target_woocommerce']
)
