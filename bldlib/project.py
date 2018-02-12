"""
Project-related classes and functions.
"""

from contextlib import contextmanager
import csv
import importlib
import io
import math
import os
import platform
import shlex
import subprocess
import sys
import timeit
import traceback

import semantic_version

from bldlib import command
from bldlib.command import CommandException
from bldlib import logger

def format_duration(duration):
    """
    Format a duration in second as a hour:minute:second string.
    """
    negative = duration < 0
    hours, remainder = divmod(math.fabs(duration), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%s%d:%02d:%02d' % ('-' if negative else '', hours, minutes, seconds)

class ProjectException(Exception):
    """
    Project-related exception.
    """
    pass

class ModuleException(Exception):
    """
    Module-related exception.
    """
    pass

def load_project(project_dir):
    """
    Loads the project definition.
    """
    if not project_dir or not os.path.exists(project_dir):
        raise ProjectException("Project directory does not exist")

    sys.path.append(project_dir)
    try:
        project_module = importlib.import_module(Project.PROJECT_MODULE)
    except ImportError as err:
        raise ProjectException(
            "No project definition (%s) in %s." % (Project.PROJECT_FILE, project_dir), err)

    if not hasattr(project_module, 'NAME'):
        raise ProjectException("No NAME attribute in project definition")
    if not hasattr(project_module, 'VERSION'):
        raise ProjectException("No VERSION attribute in project definition")
    if not hasattr(project_module, 'MODULES'):
        raise ProjectException("No MODULES attribute in project definition")
    if hasattr(project_module, 'LEGAL'):
        legal = project_module.LEGAL
    else:
        legal = 0
    if hasattr(project_module, 'BUILD_DIR'):
        build_dir = os.path.realpath(os.path.join(project_dir, project_module.BUILD_DIR))
    else:
        build_dir = os.path.realpath(os.path.join(project_dir, 'build'))
    if hasattr(project_module, 'CUSTOM_ARGS'):
        custom_args = project_module.CUSTOM_ARGS
    else:
        custom_args = []

    # Set specific environment variables
    os.environ['BLD_PROJECT_HOME'] = project_dir
    os.environ['BLD_PROJECT_NAME'] = project_module.NAME
    os.environ['BLD_PROJECT_VERSION'] = project_module.VERSION

    return Project(project_module,
                   project_module.NAME,
                   project_module.VERSION,
                   legal,
                   project_module.MODULES,
                   custom_args,
                   project_dir,
                   build_dir)

class Project:
    """
    The Project class contains all the information about the project.
    """

    PROJECT_MODULE = 'projectfile'
    PROJECT_FILE = '%s.py' % PROJECT_MODULE

    def __init__(self, projectfile, name, version, legal, modules, custom_args, root_dir, build_dir):
        self._logger = logger.Logger()
        if not projectfile:
            raise ProjectException("Invalid projectfile")
        self._projectfile = projectfile
        if not name:
            raise ProjectException("Invalid project name")
        self._name = name
        try:
            self._version = semantic_version.Version(version)
        except ValueError:
            raise ProjectException("Invalid version: %s" % version)
        self._legal = legal
        if not isinstance(modules, list):
            raise ProjectException("Modules must be defined as a list")
        if not modules:
            raise ProjectException("At least one module must be defined")
        self._custom_args = custom_args
        # Directories
        if not root_dir:
            raise ProjectException("Invalid root directory")
        self._root_dir = root_dir
        if not build_dir:
            raise ProjectException("Invalid build directory")
        self._build_dir = build_dir
        self._install_dir = os.path.realpath(os.path.join(self._build_dir, 'release'))
        self._dist_dir = os.path.realpath(os.path.join(self._build_dir, 'dist'))
        self._report_dir = os.path.realpath(os.path.join(self._build_dir, 'report'))
        # Thinks that may depends on directories being set
        self._load_modules(modules)
        self._modules = modules
        self._time_report = TimeReport()

    @property
    def logger(self):
        """
        Returns the logger.
        """
        return self._logger

    @property
    def name(self):
        """
        Returns the name.
        """
        return self._name

    @property
    def version(self):
        """
        Returns the version.
        """
        return self._version

    @property
    def legal(self):
        """
        Returns the legal.
        """
        return self._legal

    @property
    def modules(self):
        """
        Returns the modules.
        """
        return self._modules

    @property
    def custom_args(self):
        """
        Returns the custom_args.
        """
        return self._custom_args

    @property
    def root_dir(self):
        """
        Returns the root_dir.
        """
        return self._root_dir

    @property
    def build_dir(self):
        """
        Returns the build_dir.
        """
        return self._build_dir

    @build_dir.setter
    def build_dir(self, value):
        """
        Sets the build_dir.
        """
        if os.path.isabs(value):
            self._build_dir = os.path.realpath(value)
        else:
            self._build_dir = os.path.realpath(os.path.join(self.root_dir, value))

    @property
    def install_dir(self):
        """
        Returns the install_dir.
        """
        return self._install_dir

    @install_dir.setter
    def install_dir(self, value):
        """
        Sets the install_dir.
        """
        if os.path.isabs(value):
            self._install_dir = os.path.realpath(value)
        else:
            self._install_dir = os.path.realpath(os.path.join(self.build_dir, value))

    @property
    def dist_dir(self):
        """
        Returns the dist_dir.
        """
        return self._dist_dir

    @dist_dir.setter
    def dist_dir(self, value):
        """
        Sets the dist_dir.
        """
        if os.path.isabs(value):
            self._dist_dir = os.path.realpath(value)
        else:
            self._dist_dir = os.path.realpath(os.path.join(self.build_dir, value))

    @property
    def report_dir(self):
        """
        Returns the report_dir.
        """
        return self._report_dir

    @property
    def time_report(self):
        """
        Returns the time_report.
        """
        return self._time_report

    @contextmanager
    def chdir(self, dir_path):
        """
        Change working directory for the context.
        """
        old_dir = os.getcwd()
        if dir_path != old_dir:
            os.chdir(dir_path)
            self._logger.debug("Now in %s", os.getcwd())
        try:
            yield
        finally:
            if dir_path != old_dir:
                os.chdir(old_dir)
                self._logger.debug("Now in %s", os.getcwd())

    def run(self, cmd):
        """
        Runs the given command.
        """
        command.run(cmd, self._logger)

    @contextmanager
    def step(self, name, description):
        """
        Runs commands in a monitored step.
        """
        begin = timeit.default_timer()
        self._logger.info("=== %s", description)
        try:
            yield
        finally:
            self._time_report.add(name, timeit.default_timer() - begin)

    def shell(self, args):
        """
        Open an interactive shell
        """
        # Call the project's environment function
        try:
            importlib.import_module('env')
            self._call(['env'], 'setenv', args)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % ('env', err))

        if platform.system() == 'Windows':
            print("Type 'exit' to return\n")
            os.environ['PROMPT'] = "(%s) %s" % (self.name, os.environ['PROMPT'])
            subprocess.call(['cmd', '/k'])
        else:
            print("Type 'exit' or press 'Ctrl+D' to return\n")
            subprocess.call([os.getenv('SHELL'), '-i'])
            print("Shell exited\n")


    def execute(self, args, cmd):
        """
        Execute the command in the project environment and returns the its return code.
        """
        # Call the project's environment function
        try:
            importlib.import_module('env')
            self._call(['env'], 'setenv', args)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % ('env', err))

        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        self.logger.debug("Running command %s", shlex.quote(' '.join(cmd)))
        return subprocess.call(cmd)


    def build(self, args, modules):
        """
        Build the project.
        """
        with self.chdir(self.root_dir):
            begin = timeit.default_timer()
            try:
                if not os.path.exists(self.build_dir):
                    os.makedirs(self.build_dir)
                if args.prepare:
                    self.prepare_release(args, args.prepare, args.next_version)
                elif args.tag:
                    self.tag(args, args.tag, args.k)
                elif args.set_version:
                    self.set_version(args, args.set_version)
                else:
                    # Call the project's environment function
                    try:
                        module_name = 'env'
                        importlib.import_module(module_name)
                        self._call([module_name], 'setenv', args)
                    except ImportError as err:
                        raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))

                    has_command = False
                    if args.clean:
                        self._call(modules, 'clean', args)
                        has_command = True
                    if args.build:
                        self._call(modules, 'build', args)
                        has_command = True
                    if args.install:
                        self._call(modules, 'install', args)
                        has_command = True
                    if args.package:
                        self._call(modules, 'package', args)
                        has_command = True
                    if args.deliver:
                        self._call(modules, 'deliver', args)
                        has_command = True
                    if args.test:
                        self._call(modules, 'test', args)
                        has_command = True
                    if not has_command:
                        # By default, call build
                        self._call(modules, 'build', args)
                status = 'successful'
            except (ProjectException, ModuleException, CommandException) as ex:
                self._logger.error(ex.args[0])
                status = 'failed'
            except Exception as ex:
                buffer = io.StringIO()
                traceback.print_exc(file=buffer)
                self._logger.error(buffer.getvalue())
                status = 'failed'
            finally:
                # Record execution time
                elapsed = timeit.default_timer() - begin
                self._time_report.add('total', elapsed)
                # Save time report
                if not os.path.exists(self.report_dir):
                    os.makedirs(self.report_dir)
                self._time_report.save_csv(os.path.join(self.report_dir, 'times.csv'))
        self._logger.log("Build %s in %s.", status, format_duration(elapsed))
        return 0 if status == 'successful' else 1


    def prepare_release(self, args, new_version, next_version=None):
        """
        Prepare the release. It creates a release branch and update the project version.
        """
        # Call the project's environment function
        try:
            module_name = 'env'
            importlib.import_module(module_name)
            self._call([module_name], 'setenv', args)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))

        # Call the project's prepare_release function
        try:
            module_name = 'management'
            importlib.import_module(module_name)
            func = getattr(sys.modules[module_name], 'prepare_release')
            try:
                new_version = semantic_version.Version(new_version)
                if next_version:
                    next_version = semantic_version.Version(next_version)
                func(self, new_version, next_version)
            except ValueError:
                raise ProjectException("Invalid version: %s" % new_version)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))


    def tag(self, args, version, is_pre_release):
        """
        Tag the project.
        """
        # Call the project's environment function
        try:
            module_name = 'env'
            importlib.import_module(module_name)
            self._call([module_name], 'setenv', args)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))

        # Call the project's tag function
        try:
            module_name = 'management'
            importlib.import_module(module_name)
            func = getattr(sys.modules[module_name], 'tag')
            try:
                func(self, semantic_version.Version(version), is_pre_release)
            except ValueError:
                raise ProjectException("Invalid version: %s" % version)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))


    def set_version(self, args, version):
        """
        Change the project's version.
        """
        # Call the project's environment function
        try:
            module_name = 'env'
            importlib.import_module(module_name)
            self._call([module_name], 'setenv', args)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))

        # Call the project's update_version function
        try:
            module_name = 'management'
            importlib.import_module(module_name)
            func = getattr(sys.modules[module_name], 'update_version')
            try:
                func(self, semantic_version.Version(version))
            except ValueError:
                raise ProjectException("Invalid version: %s" % version)
        except ImportError as err:
            raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))

    def _load_modules(self, modules):
        # The module scripts are expected to be in the bld directory
        sys.path.append(os.path.join(self.root_dir, 'bld'))
        for module_name in modules:
            try:
                # Just import the module, it can then be access with sys.modules[name]
                importlib.import_module(module_name)
            except ImportError as err:
                raise ProjectException('Module \'%s\' not found: %s' % (module_name, err))


    def _call(self, modules, func_name, args):
        """
        Calls the given function in the given modules.
        """
        for module_name in modules:
            module = sys.modules[module_name]
            if not hasattr(module, func_name):
                raise ModuleException(
                    "Module %s does not define a '%s' function." % (module_name, func_name))
            self._logger.info("%s:%s" % (module_name, func_name))
            func = getattr(module, func_name)
            func(self, args)


class TimeReport:
    """
    A time execution report.
    """

    def __init__(self):
        self._steps = []
        self._records = {}

    def add(self, name, elapsed):
        """
        Add a record.
        """
        self._steps.append(name)
        self._records[name] = elapsed

    def save_csv(self, file_path):
        """
        Save the report as csv to the giben file.
        """
        with open(file_path, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, self._steps)
            writer.writeheader()
            writer.writerow(self._records)
