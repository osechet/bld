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

    target = args.target if args.target else get_default_target()

    module_dir = os.path.join(project.root_dir, 'server')
    with project.chdir(module_dir):
        with project.step('configuration', "Configuration"):
            run('echo "Building for %s..."' % target)
            run('sleep 3')

        with project.step('misc', "Misc"):
            run('bash -c "echo \'Doing something\' && echo \'Running a failing command...\' && false"')

def get_default_target():
    """
    Returns the default target for the current platform.
    """
    if platform.system() == 'Linux':
        return 'rhel6'
    elif platform.system() == 'Windows':
        return 'win7'
    return 'rhel6'
