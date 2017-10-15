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
        with project.step('build', "Build"):
            run('echo "Building..."')
            run('sleep 2')

        with project.step('install', "Installation"):
            run('echo "Installing..."')
            run('sleep 1')
