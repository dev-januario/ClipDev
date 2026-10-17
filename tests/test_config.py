"""Testes das preferências (config.load_settings/save_settings/clamp_font)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipdev import config  # noqa: E402


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    s = config.load_settings()
    assert s["font_size"] == config.FONT_DEFAULT


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    config.save_settings({"font_size": 16})
    s = config.load_settings()
    assert s["font_size"] == 16


def test_clamp_low(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    config.save_settings({"font_size": 1})
    assert config.load_settings()["font_size"] == config.FONT_MIN


def test_clamp_high(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    config.save_settings({"font_size": 999})
    assert config.load_settings()["font_size"] == config.FONT_MAX


def test_invalid_json_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    config.config_path().write_text("{ isso não é json", encoding="utf-8")
    assert config.load_settings()["font_size"] == config.FONT_DEFAULT


def test_clamp_font_helper():
    assert config.clamp_font(3) == config.FONT_MIN
    assert config.clamp_font(50) == config.FONT_MAX
    assert config.clamp_font(13) == 13