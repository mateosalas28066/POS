"""Fixtures and configuration for caja tests."""
import pytest


@pytest.fixture(autouse=True)
def mock_qmessagebox(monkeypatch):
    """Auto-mock QMessageBox to prevent blocking in headless tests."""
    from unittest.mock import Mock
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", Mock())
    monkeypatch.setattr(QMessageBox, "critical", Mock())
    monkeypatch.setattr(QMessageBox, "warning", Mock())
