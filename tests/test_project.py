"""
Basic test
"""

import os
from unittest import mock

import pytest
import semantic_version

from bldlib import project
from bldlib.project import Project, ProjectException


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
    def test_projectfile(self, mock_exists, mock_import_module):
        class Projectfile:
            NAME = 'test'
            VERSION = '0.1.0-dev'
            MODULES = ['main']
            BUILD_DIR = '../build'
        mock_exists.return_value = True
        mock_import_module.return_value = Projectfile()

        project_path = os.path.join(os.environ['HOME'], 'test_project')
        proj = project.load_project(project_path)
        assert proj.root_dir == project_path
        assert proj.build_dir == os.path.abspath(os.path.join(project_path, '../build'))

class TestProject:

    def test_invalid_projectfile(self):
        with pytest.raises(ProjectException) as exc_info:
            Project(None, None, None, None, None, None, None)
        assert exc_info.value.args[0] == "Invalid projectfile"

    def test_invalid_name(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, None, None, None, None, None, None)
        assert exc_info.value.args[0] == "Invalid project name"

    def test_invalid_version(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', None, None, None, None, None)
        assert exc_info.value.args[0] == "Invalid version: None"
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', 'dev', None, None, None, None)
        assert exc_info.value.args[0] == "Invalid version: dev"

    def test_invalid_modules(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', None, None, None, None)
        assert exc_info.value.args[0] == "Modules must be defined as a list"

    def test_invalid_root_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', ['main'], None, None, None)
        assert exc_info.value.args[0] == "Invalid root directory"

    def test_invalid_build_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', ['main'], None, 'test', None)
        assert exc_info.value.args[0] == "Invalid build directory"

    @mock.patch('importlib.import_module')
    def test_valid_project(self, mock_import_module):
        # Used to mock module load
        mock_import_module.return_value = {}

        project_path = os.path.join(os.environ['HOME'], 'test')
        project = Project({'NAME':'test'}, 'test', '0.1.0-dev', ['main'],
                          ['--custom'], project_path, os.path.join(project_path, 'build'))
        assert project.name == 'test'
        assert project.version == semantic_version.Version('0.1.0-dev')
        assert project.modules == ['main']
        assert project.custom_args == ['--custom']
        assert project.root_dir == project_path
        assert project.build_dir == os.path.join(project_path, 'build')
        assert project.install_dir == os.path.join(project_path, 'build', 'release')
        assert project.dist_dir == os.path.join(project_path, 'build', 'dist')
        assert project.report_dir == os.path.join(project_path, 'build', 'report')
        assert not project.time_report is None
