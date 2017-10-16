#!/usr/bin/env python3
"""
Build helper command.
"""

import argparse
import logging
import os

from bldlib.project import load_project, ModuleException, ProjectException
from bldlib.logger import ColoredFormatter

ERR_CODE_CANNOT_LOAD_PROJECT = 1
ERR_CODE_INVALID_ARGUMENTS = 2
ERR_CODE_EXECUTION_ERROR = 3


def init_logging():
    """
    Init the logs.
    """
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = ColoredFormatter()
    console.setFormatter(formatter)
    root_logger.addHandler(console)
    return console


def run():
    """
    The main function.
    """
    handler = init_logging()

    # Project creation
    try:
        project_dir = get_project_dir()
        project = load_project(project_dir)
    except ProjectException as ex:
        logging.getLogger('bld').error(ex.args[0])
        exit(ERR_CODE_CANNOT_LOAD_PROJECT)

    # From here the project is initialized and we can use its logger
    logger = project.logger

    parser = argparse.ArgumentParser(description="Build Helper")
    modules_group = parser.add_argument_group('Modules')
    if project.modules:
        modules_group.add_argument('modules', nargs='*', choices=[[]] + project.modules,
                                help="""The available modules. Build all the modules
                                if none is provided.""")
    options_group = parser.add_argument_group('Options')
    options_group.add_argument('-c', '--clean', action='store_true',
                               help="Clean the project")
    options_group.add_argument('-b', '--build', action='store_true',
                               help="Build the project")
    options_group.add_argument('-i', '--install', action='store_true',
                               help="Install the project")
    options_group.add_argument('-p', '--package', action='store_true',
                               help="Package the project")
    options_group.add_argument('--release',
                               help="Prepare the release of the project")
    options_group.add_argument('--tag',
                               help="Tag the project with the given TAG")
    options_group.add_argument('-k', action='store_true',
                               help="""Used with --tag to tag a pre-release.
                               When tagging a pre-release, the release branch
                               is kept opened.""")
    build_group = parser.add_argument_group('Build Modifiers')
    build_group.add_argument('-D', '--build-dir',
                             help="The build directory.", default=project.build_dir)
    build_group.add_argument('--install-dir',
                             help="The install directory.", default=project.install_dir)
    build_group.add_argument('--dist-dir',
                             help="The distribution directory.", default=project.dist_dir)
    log_group = parser.add_argument_group('Logs')
    log_group.add_argument('-v', '--verbose', action='store_true',
                           help="Increase verbosity")
    log_group.add_argument('-d', '--debug', action='store_true',
                           help="Enable debug logs")
    custom_group = parser.add_argument_group('Custom')
    for custom_arg in project.custom_args:
        short_desc = custom_arg.get('short_desc')
        long_desc = custom_arg.get('long_desc')
        help_text = custom_arg.get('help')
        if short_desc and long_desc:
            custom_group.add_argument(short_desc, long_desc, help=help_text)
        elif short_desc:
            custom_group.add_argument(short_desc, help=help_text)
        else:
            custom_group.add_argument(long_desc, help=help_text)
    args = parser.parse_args()

    # Validate arguments
    if args.k and not args.tag:
        logger.error("-k can only be used with --tag")
        exit(ERR_CODE_INVALID_ARGUMENTS)

    # Enable verbosity
    logger.verbose = args.verbose

    # Enable debug log
    if args.debug:
        handler.setLevel(logging.DEBUG)
    logger.debug("%s", args)

    # Check modules to build
    if not hasattr(args, 'modules') or not args.modules:
        modules = project.modules
    else:
        modules = args.modules

    # Directories
    if args.build_dir:
        project.build_dir = args.build_dir
    if args.install_dir:
        project.install_dir = args.install_dir

    # Summary
    logger.debug("==========")
    logger.debug("Name:              %s", project.name)
    logger.debug("Version:           %s", project.version)
    logger.debug("Root directory:    %s", project.root_dir)
    logger.debug("Build directory:   %s", project.build_dir)
    logger.debug("Install directory: %s", project.install_dir)
    logger.debug("Dist. directory:   %s", project.dist_dir)
    logger.debug("Report directory:  %s", project.report_dir)
    logger.debug("Modules:           %s", ', '.join(modules))
    logger.debug("==========")

    # Build
    try:
        project.build(args, modules)
    except ModuleException as ex:
        logger.error(ex.args[0])
        exit(ERR_CODE_EXECUTION_ERROR)


def get_project_dir():
    """
    Returns the project root directory expecting a PROJECT_HOME venv ariable to be defined.
    """
    if not os.environ.get('PROJECT_HOME'):
        raise ProjectException("No PROJECT_HOME environment variable defined.")
    return os.path.abspath(os.environ['PROJECT_HOME'])
