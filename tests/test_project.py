"""
Basic test
"""

# from unittest import mock
# from unittest.mock import call
import unittest

import pytest
import semantic_version

from bldlib.project import Project, ProjectException

class TestProject(object):

    def test_invalid_projectfile(self):
        with pytest.raises(ProjectException) as exc_info:
            Project(None, None, None, None, None, None)
        assert exc_info.value.args[0] == "Invalid projectfile"

    def test_invalid_name(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, None, None, None, None, None)
        assert exc_info.value.args[0] == "Invalid project name"

    def test_invalid_version(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', None, None, None, None)
        assert exc_info.value.args[0] == "Invalid version: None"
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', 'dev', None, None, None)
        assert exc_info.value.args[0] == "Invalid version: dev"

    def test_invalid_modules(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', None, None, None)
        assert exc_info.value.args[0] == "Modules must be defined as a list"

    def test_invalid_root_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', [], None, None)
        assert exc_info.value.args[0] == "Invalid root directory"

    def test_invalid_build_dir(self):
        with pytest.raises(ProjectException) as exc_info:
            Project({'NAME':'test'}, 'test', '0.1.0-dev', [], 'test', None)
        assert exc_info.value.args[0] == "Invalid build directory"

    def test_valid_project(self):
        project = Project({'NAME':'test'}, 'test', '0.1.0-dev', [], 'test', 'test/build')
        assert project.name == 'test'
        assert project.version == semantic_version.Version('0.1.0-dev')
        assert project.root_dir == 'test'
        assert project.build_dir == 'test/build'
        assert project.install_dir == 'test/release'
        assert project.dist_dir == 'test/dist'
        assert project.report_dir == 'test/report'
        assert project.modules == []
        assert not project.time_report is None
