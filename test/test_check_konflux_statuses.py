"""Tests for check_konflux_statuses."""

import types
from pathlib import Path

import pytest


@pytest.fixture
def cks_module():
    """Load check_konflux_statuses.py as a Python module."""
    script_path = Path(__file__).parent.parent / "ci" / "check_konflux_statuses.py"
    module = types.ModuleType("check_konflux_statuses")
    module.__file__ = str(script_path)
    code = compile(script_path.read_text(), str(script_path), "exec")
    exec(code, module.__dict__)
    return module


class TestFilterKonfluxStatuses:
    """Tests for filter_konflux_statuses."""

    def test_matches_build_pipeline(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "success",
            },
            {"name": "check", "status": "success"},
            {"name": "tree_status", "status": "success"},
        ]
        result = cks_module.filter_konflux_statuses(statuses)
        assert len(result) == 1
        assert result[0]["name"] == "Konflux kflux-prd-rh03 / ruff-main-on-pull-request"

    def test_ignores_testing_farm(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "success",
            },
            {
                "name": "Red Hat Konflux / rpms-main-testing-farm-aarch64 / ruff-main",
                "status": "pending",
            },
            {
                "name": "Red Hat Konflux / rpms-main-testing-farm-x86-64 / ruff-main",
                "status": "pending",
            },
        ]
        result = cks_module.filter_konflux_statuses(statuses)
        assert len(result) == 1
        assert "kflux-prd-rh03" in result[0]["name"]

    def test_returns_empty_when_no_konflux_statuses(self, cks_module):
        statuses = [
            {"name": "check", "status": "success"},
            {"name": "tree_status", "status": "success"},
        ]
        assert cks_module.filter_konflux_statuses(statuses) == []

    def test_returns_empty_for_empty_input(self, cks_module):
        assert cks_module.filter_konflux_statuses([]) == []

    def test_handles_missing_name_field(self, cks_module):
        statuses = [{"status": "success"}, {"name": None, "status": "success"}]
        assert cks_module.filter_konflux_statuses(statuses) == []

    def test_multiple_packages(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / golang1-25-main-on-pull-request",
                "status": "success",
            },
            {
                "name": "Konflux kflux-prd-rh03 / golang1-26-main-on-pull-request",
                "status": "running",
            },
        ]
        result = cks_module.filter_konflux_statuses(statuses)
        assert len(result) == 2


class TestCheckStatuses:
    """Tests for check_statuses."""

    def test_missing_when_empty(self, cks_module):
        assert cks_module.check_statuses([]) == "missing"

    def test_invoked_when_successful(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "success",
            },
        ]
        assert cks_module.check_statuses(statuses) == "invoked"

    def test_invoked_when_pending(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "pending",
            },
        ]
        assert cks_module.check_statuses(statuses) == "invoked"

    def test_invoked_when_running(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "running",
            },
        ]
        assert cks_module.check_statuses(statuses) == "invoked"

    def test_failed_when_failed(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / ruff-main-on-pull-request",
                "status": "failed",
            },
        ]
        assert cks_module.check_statuses(statuses) == "failed"

    def test_failed_when_mixed(self, cks_module):
        statuses = [
            {
                "name": "Konflux kflux-prd-rh03 / golang1-25-main-on-pull-request",
                "status": "success",
            },
            {
                "name": "Konflux kflux-prd-rh03 / golang1-26-main-on-pull-request",
                "status": "failed",
            },
        ]
        assert cks_module.check_statuses(statuses) == "failed"
