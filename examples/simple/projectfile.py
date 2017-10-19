"""
Project definition.
"""

NAME = 'super-project'
VERSION = '0.1.0-dev'
LEGAL = 'Copyright (c) 2003-2017 Sercel. All rights reserved.'
MODULES = ['client', 'server']
BUILD_DIR = 'build'
CUSTOM_ARGS = [
    {'long_desc': '--target', 'help': 'The target', 'choices': ['rhel6', 'win7']},
]
