"""
Project-related classes and functions.
"""

from contextlib import contextmanager
import csv
import importlib
import math
import os
import sys
import timeit

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
        project_module = importlib.import_module('projectfile')
    except ImportError as err:
        raise ProjectException(
            "No project definition (projectfile.py) in %s." % project_dir, err)

    if not hasattr(project_module, 'NAME'):
        raise ProjectException("No NAME attribute in project definition")
    if not hasattr(project_module, 'VERSION'):
        raise ProjectException("No VERSION attribute in project definition")
    if not hasattr(project_module, 'MODULES'):
        raise ProjectException("No MODULES attribute in project definition")
    if hasattr(project_module, 'BUILD_DIR'):
        build_dir = os.path.realpath(os.path.join(project_dir, project_module.BUILD_DIR))
    else:
        build_dir = os.path.realpath(os.path.join(project_dir, 'build'))
    if hasattr(project_module, 'CUSTOM_ARGS'):
        custom_args = project_module.CUSTOM_ARGS
    else:
        custom_args = []

    return Project(project_module,
                   project_module.NAME,
                   project_module.VERSION,
                   project_module.MODULES,
                   custom_args,
                   project_dir,
                   build_dir)

class Project:
    """
    The Project class contains all the information about the project.
    """

    def __init__(self, projectfile, name, version, modules, custom_args, root_dir, build_dir):
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

    def build(self, args, modules):
        """
        Build the project.
        """
        with self.chdir(self.root_dir):
            begin = timeit.default_timer()
            try:
                if not os.path.exists(self.build_dir):
                    os.makedirs(self.build_dir)
                if args.release:
                    self.prepare_release(args.release.value)
                elif args.tag:
                    self.tag(args.tag.value, args.k)
                else:
                    if args.clean:
                        func_name = 'clean'
                    elif args.build:
                        func_name = 'build'
                    elif args.install:
                        func_name = 'install'
                    elif args.package:
                        func_name = 'package'
                    else:
                        # Build by default
                        func_name = 'build'
                    self._call(modules, func_name, args)
                status = 'successful'
            except (ProjectException, ModuleException, CommandException):
                status = 'failed'
            except Exception as ex:
                self._logger.error(ex.args[0])
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

    def prepare_release(self, new_version):
        """
        Prepare the release. It creates a release branch and update the project version.
        """
        pass

    def tag(self, tag, is_pre_release):
        """
        Tag the project.
        """
        pass

    def _load_modules(self, modules):
        # The module scripts are expected to be in the bld directory
        sys.path.append(os.path.join(self.root_dir, 'bld'))
        for module_name in modules:
            try:
                # Just import the module, it can then be access with sys.modules[name]
                importlib.import_module(module_name)
            except ImportError:
                raise ProjectException('Module \'%s\' not found' % module_name)

    def _call(self, modules, func_name, args):
        """
        Calls the given function in the given modules.
        """
        for module_name in modules:
            module = sys.modules[module_name]
            if not hasattr(module, func_name):
                raise ModuleException(
                    "Module %s does not define a '%s' function." % (module_name, func_name))
            self._logger.log("%s:%s" % (module_name, func_name))
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
