# Bld

[![Build Status](https://travis-ci.org/osechet/bld.svg?branch=master)](https://travis-ci.org/osechet/bld)
[![codecov](https://codecov.io/gh/osechet/bld/branch/master/graph/badge.svg)](https://codecov.io/gh/osechet/bld)

Bld is a project build helper. It is mainly aimed at complex project composed by modules with different languages.

A typical project example is a client/server project where the server is coded with one language (C++, Go, Python...) and the client in another (Java, Javascript...). Both modules uses their own build system that can rarely be the same. To build the whole project, you end by creating a lot of scripts that cover the main situations.

Bld can be used to avoid the creation of all those scripts. Just create a Python module for each project's module where you describe how to build it.

## Installation

* From source:
```
git clone https://github.com/osechet/bld
cd bld
python setup.py install
```

## Usage

* At the root of your project, create a `projectfile.py` file:
```python
"""
Project definition.
"""

NAME = 'super-project'
VERSION = '0.1.0-dev'
MODULES = ['client', 'server']
BUILD_DIR = 'build'
```

* Set the `PROJECT_HOME` environment variable to define the root directory of your project:
```bash
export PROJECT_HOME="/path/to/super-project"
```

* Create a script for each project module in the `${PROJECT_HOME}/bld` directory:

client.py:
```python
"""
The client module.
"""

import os

def build(project, args):
    """
    Build the module.
    """
    # Aliases
    run = project.run

    module_dir = os.path.join(project.root_dir, 'client')
    with project.chdir(module_dir):
        with project.step('client:build', "Build"):
            run('echo "Building..."')
            run('sleep 2')
```

server.py:
```python
"""
The server module.
"""

import os
import platform

def build(project, args):
    """
    Build the module.
    """
    # Aliases
    run = project.run

    module_dir = os.path.join(project.root_dir, 'server')
    with project.chdir(module_dir):
        with project.step('server:build', "Build"):
            run('echo "Building..."')
            run('sleep 3')
```

* Call `bld` to build the whole project or `bld <module>` to build a specific module.

### Reports

Bld automatically monitor the time execution of the build. The result is stored at the end of the build in the `reports/time.csv` file. The project's `step()` method can be used to monitor a specific block of code. The time report list all the executed steps by name but also the total build execution:
```csv
client:build,server:build,total
2.015258717990946,3.018017319991486,5.0884078509989195
```

## Development

* Install dev requirements:
```
pip install -r requirements_dev.txt
```

### Unit tests

To run unit tests, call `py.test`. For code coverage, run `py.test --cov=bldlib`.
