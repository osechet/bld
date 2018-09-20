"""
Basic test
"""

import os
from unittest import mock

import pytest
import semantic_version

from bldlib import project
from bldlib.project import Project, ProjectException

def test_format_duration():
    assert project.format_duration(0) == '0:00:00'
    assert project.format_duration(12 * 3600 + 34 * 60 + 56) == '12:34:56'
    assert project.format_duration(-1) == '-0:00:01'
    assert project.format_duration(-(12 * 3600 + 34 * 60 + 56)) == '-12:34:56'

class TestLoadProject:

    def test_invalid_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            project.load_project(None)
        assert exc_info.value.args[0] == "Project directory does not exist"

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_no_projectfile(self, mock_exists, mock_import_module):
        mock_exists.return_value = True
        mock_import_module.side_effect = ImportError("")

        with pytest.raises(ProjectException) as exc_info:
            project.load_project('project_path')
        assert exc_info.value.args[0] == "No project definition (projectfile.py) in project_path."

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile_no_name(self, mock_exists, mock_import_module):
        class Projectfile:
            pass
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        with pytest.raises(ProjectException) as exc_info:
            project.load_project('project_path')
        assert exc_info.value.args[0] == "No NAME attribute in project definition"

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile_no_version(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        with pytest.raises(ProjectException) as exc_info:
            project.load_project('project_path')
        assert exc_info.value.args[0] == "No VERSION attribute in project definition"

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile_no_modules(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
            VERSION = '0.1.0-dev'
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        with pytest.raises(ProjectException) as exc_info:
            project.load_project('project_path')
        assert exc_info.value.args[0] == "No MODULES attribute in project definition"

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile_no_build_dir(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
            VERSION = '0.1.0-dev'
            MODULES = ['main']
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        project_path = os.path.join(os.environ['HOME'], 'test_project')
        p = project.load_project(project_path)
        assert p.build_dir == os.path.join(project_path, 'build')

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile_no_custom_args(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
            VERSION = '0.1.0-dev'
            MODULES = ['main']
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        project_path = os.path.join(os.environ['HOME'], 'test_project')
        p = project.load_project(project_path)
        assert p.custom_args == []

    @mock.patch('importlib.import_module')
    @mock.patch('os.path.exists')
    def test_projectfile(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
            VERSION = '0.1.0-dev'
            MODULES = ['main']
            BUILD_DIR = '../build'
            LEGAL = 'Copyright (c) 2018 Olivier Sechet'
            CUSTOM_ARGS = [{'--custom'}]
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        project_path = os.path.join(os.environ['HOME'], 'test_project')
        proj = project.load_project(project_path)
        assert proj.root_dir == project_path
        assert proj.build_dir == os.path.abspath(
            os.path.join(project_path, '../build'))
        assert proj.custom_args == [{'--custom'}]


class TestProject:

    def test_invalid_projectfile(self):
        with pytest.raises(ProjectException) as exc_info:
            Project(None, None, None, None,
                    None, None, None, None)
        assert exc_info.value.args[0] == "Invalid projectfile"

    def test_invalid_name(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, None, None, None,
                    None, None, None, None)
        assert exc_info.value.args[0] == "Invalid project name"

    def test_invalid_version(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', None, None,
                    None, None, None, None)
        assert exc_info.value.args[0] == "Invalid version: None"
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', 'dev', None,
                    None, None, None, None)
        assert exc_info.value.args[0] == "Invalid version: dev"

    def test_invalid_modules(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                    None, None, None, None)
        assert exc_info.value.args[0] == "Modules must be defined as a list"

    def test_no_modules(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                    [], None, None, None)
        assert exc_info.value.args[0] == "At least one module must be defined"

    def test_invalid_root_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                    ['main'], None, None, None)
        assert exc_info.value.args[0] == "Invalid root directory"

    def test_invalid_build_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                    ['main'], None, 'test', None)
        assert exc_info.value.args[0] == "Invalid build directory"

    @mock.patch('importlib.import_module')
    def test_valid_project(self, mock_import_module):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev',
                       'Copyright (c) 2018 Olivier Sechet',
                       ['main'], [{'--custom'}], project_path,
                       os.path.join(project_path, 'build'))
        assert proj.logger
        assert proj.name == 'test'
        assert proj.version == semantic_version.Version('0.1.0-dev')
        assert proj.legal == 'Copyright (c) 2018 Olivier Sechet'
        assert proj.modules == ['main']
        assert proj.custom_args == [{'--custom'}]
        assert proj.root_dir == project_path
        assert proj.build_dir == os.path.join(project_path, 'build')
        assert proj.install_dir == os.path.join(project_path,
                                                'build', 'release')
        assert proj.dist_dir == os.path.join(project_path, 'build', 'dist')
        assert proj.report_dir == os.path.join(project_path, 'build', 'report')
        assert proj.time_report

    @mock.patch('importlib.import_module')
    def test_set_build_dir(self, mock_import_module):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))
        proj.build_dir = 'build'
        assert proj.build_dir == os.path.join(project_path, 'build')

        proj.build_dir = os.path.join(os.path.dirname(project_path), 'other_build')
        assert proj.build_dir == os.path.join(os.path.dirname(project_path), 'other_build')

    @mock.patch('importlib.import_module')
    def test_set_install_dir(self, mock_import_module):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))
        proj.install_dir = 'release'
        assert proj.install_dir == os.path.join(proj.build_dir, 'release')

        proj.install_dir = os.path.join(os.path.dirname(project_path), 'release')
        assert proj.install_dir == os.path.join(os.path.dirname(project_path), 'release')

    @mock.patch('importlib.import_module')
    def test_set_dist_dir(self, mock_import_module):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))
        proj.dist_dir = 'dist'
        assert proj.dist_dir == os.path.join(proj.build_dir, 'dist')

        proj.dist_dir = os.path.join(os.path.dirname(project_path), 'dist')
        assert proj.dist_dir == os.path.join(os.path.dirname(project_path), 'dist')

    @mock.patch('os.chdir')
    @mock.patch('os.getcwd')
    @mock.patch('importlib.import_module')
    def test_chdir(self, mock_import_module, mock_getcwd, mock_chdir):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))
        mock_getcwd.side_effect = ['foo', 'foo/bar', 'foo']

        with proj.chdir('bar'):
            pass
        mock_chdir.assert_has_calls([mock.call('bar'), mock.call('foo')])

    @mock.patch('os.chdir')
    @mock.patch('os.getcwd')
    @mock.patch('importlib.import_module')
    def test_chdir_same_dir(self, mock_import_module, mock_getcwd, mock_chdir):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))
        mock_getcwd.side_effect = ['foo']

        with proj.chdir('foo'):
            pass
        mock_chdir.assert_not_called()

    @mock.patch('bldlib.command.run')
    @mock.patch('importlib.import_module')
    def test_run(self, mock_import_module, mock_command_run):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))

        proj.run('echo foo')
        mock_command_run.assert_called_with('echo foo', proj.logger)

    @mock.patch('bldlib.project.TimeReport')
    @mock.patch('bldlib.logger.Logger')
    @mock.patch('timeit.default_timer')
    @mock.patch('importlib.import_module')
    def test_step(self, mock_import_module, mock_timer, MockLogger, MockTimeReport):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        proj = Project({'NAME': 'test'}, 'test', '0.1.0-dev', None,
                       ['main'], ['--custom'], project_path,
                       os.path.join(project_path, 'build'))

        mock_timer.side_effect = [2, 4]
        with proj.step('name', 'description'):
            pass
        proj.logger.info.assert_called_with('=== %s', 'description')
        proj.time_report.add.assert_called_with('name', 2)
