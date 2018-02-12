#!/usr/bin/env python3
"""
Build helper command.
"""

import argparse
import logging
import os

import colorama

from bldlib.project import load_project, ModuleException, Project, ProjectException
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
    # Enable color on Windows
    colorama.init()

    # Initialize default logger
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
    info_group = parser.add_argument_group('Informations')
    info_group.add_argument('--project-name', action='store_true',
                            help="Print the project's name")
    info_group.add_argument('--project-version', action='store_true',
                            help="Print the project's version")
    options_group = parser.add_argument_group('Options')
    options_group.add_argument('-s', '--shell', action='store_true',
                               help="Open an interactive shell with the project environment")
    options_group.add_argument('-e', '--execute',
                               help="Execute the given command in the project environment")
    options_group.add_argument('-c', '--clean', action='store_true',
                               help="Clean the project")
    options_group.add_argument('-b', '--build', action='store_true',
                               help="Build the project")
    options_group.add_argument('-i', '--install', action='store_true',
                               help="Install the project")
    options_group.add_argument('-p', '--package', action='store_true',
                               help="Package the project")
    options_group.add_argument('-l', '--deliver', action='store_true',
                               help="Create the project deliverable")
    options_group.add_argument('-t', '--test', action='store_true',
                               help="Run integration tests")
    options_group.add_argument('--prepare',
                               help="Prepare the release of the project")
    options_group.add_argument('--next-version',
                               help="The next iteration version when preparing a release")
    options_group.add_argument('--set-version',
                               help="Change the project's version")
    options_group.add_argument('--tag',
                               help="Tag the project with the given version")
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
    log_group.add_argument('--log-file', help="Send the logs to provided file")
    custom_group = parser.add_argument_group('Custom')
    for custom_arg in project.custom_args:
        short_desc = custom_arg.get('short_desc')
        long_desc = custom_arg.get('long_desc')
        help_text = custom_arg.get('help')
        choices = custom_arg.get('choices')
        action = 'store_true' if custom_arg.get('flag') else None
        if choices:
            if short_desc and long_desc:
                custom_group.add_argument(short_desc, long_desc, help=help_text, choices=choices)
            elif short_desc:
                custom_group.add_argument(short_desc, help=help_text, choices=choices)
            else:
                custom_group.add_argument(long_desc, help=help_text, choices=choices)
        else:
            if short_desc and long_desc:
                custom_group.add_argument(short_desc, long_desc, help=help_text, action=action)
            elif short_desc:
                custom_group.add_argument(short_desc, help=help_text, action=action)
            else:
                custom_group.add_argument(long_desc, help=help_text, action=action)
    args = parser.parse_args()

    # Validate arguments
    if args.k and not args.tag:
        logger.error("-k can only be used with --tag")
        exit(ERR_CODE_INVALID_ARGUMENTS)
    if args.next_version and not args.prepare:
        logger.error("--next_version can only be used with --prepare")
        exit(ERR_CODE_INVALID_ARGUMENTS)

    if args.log_file:
        logger.log("Logs written into %s" % args.log_file)
        handler.flush()
        # If log-file is given, automatically set verbose
        args.verbose = True
        root_logger = logging.getLogger('')
        log_file = logging.FileHandler(args.log_file, mode='w')
        log_file.setLevel(logging.DEBUG)
        root_logger.removeHandler(handler)
        root_logger.addHandler(log_file)

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

    if args.project_name:
        print(project.name)
        exit(0)
    if args.project_version:
        print(project.version)
        exit(0)

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

    if args.shell:
        project.shell(args)
        exit(0)

    if args.execute:
        exit(project.execute(args, args.execute))

    # Build
    try:
        exit(project.build(args, modules))
    except ModuleException as ex:
        logger.error(ex.args[0])
        exit(ERR_CODE_EXECUTION_ERROR)


def get_project_dir():
    """
    Returns the project root directory expecting a PROJECT_HOME env variable to be defined.
    If PROJECT_HOME is not defined, try to find a projectfile.py in the hierarchy.
    """
    if os.environ.get('PROJECT_HOME'):
        return os.path.abspath(os.environ['PROJECT_HOME'])

    logging.getLogger('bld').debug("PROJECT_HOME not found. Checking parent directories.")
    current_dir = os.getcwd()
    while current_dir and not os.path.exists(os.path.join(current_dir, Project.PROJECT_FILE)):
        if os.path.dirname(current_dir) == current_dir:
            # Reach the root
            current_dir = None
        else:
            current_dir = os.path.dirname(current_dir)

    if not current_dir:
        raise ProjectException("No %s found in the hierarchy and PROJECT_HOME environment variable is not defined." % Project.PROJECT_FILE)
    logging.getLogger('bld').debug("Using projectfile from: %s", current_dir)
    return current_dir
