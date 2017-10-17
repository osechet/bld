"""
The client module.
"""

import os
import time

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

        with project.step('long_op', "Long operation"):
            for i in range(1, 10):
                run('echo "Doing something - %d"' % i)
                time.sleep(0.5)
