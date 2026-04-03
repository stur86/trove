"""
Tests for the system check domain.

Uses RealSystemService with mocked subprocess/psutil for unit tests,
and FakeSystemService directly for fake-mode and env-var tests.
No real hardware requirements — all external calls are mocked or bypassed.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.system.service import (
    MODELS,
    FakeSystemService,
    RealSystemService,
    get_system_service,
    _get_viable_models,
)


# --- RealSystemService ---

def test_real_check_returns_expected_keys():
    svc = RealSystemService()
    result = svc.check()
    assert "ram_gb" in result
    assert "disk_free_gb" in result
    assert "gpu" in result
    assert "ollama_running" in result
    assert "viable_models" in result


def test_real_get_ram_gb_returns_positive_float():
    svc = RealSystemService()
    result = svc._get_ram_gb()
    assert isinstance(result, float)
    assert result > 0


def test_real_get_disk_free_gb_returns_non_negative():
    svc = RealSystemService()
    result = svc._get_disk_free_gb()
    assert isinstance(result, float)
    assert result >= 0


def test_real_get_gpu_info_no_nvidia():
    svc = RealSystemService()
    with patch("backend.system.service.shutil.which", return_value=None):
        result = svc._get_gpu_info()
    assert result["available"] is False
    assert result["vram_gb"] is None


def test_real_get_gpu_info_nvidia_present():
    svc = RealSystemService()
    mock_result = MagicMock(returncode=0, stdout="8192\n")
    with patch("backend.system.service.shutil.which", return_value="/usr/bin/nvidia-smi"):
        with patch("backend.system.service.subprocess.run", return_value=mock_result):
            result = svc._get_gpu_info()
    assert result["available"] is True
    assert result["vram_gb"] == pytest.approx(8.0, abs=0.1)


# --- _get_viable_models ---

def test_viable_models_3gb_ram():
    result = _get_viable_models(ram_gb=3.0, gpu_info={"available": False, "vram_gb": None})
    assert result == []


def test_viable_models_6gb_ram():
    result = _get_viable_models(ram_gb=6.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:e4b" in tags
    assert "gemma4:31b" not in tags


def test_viable_models_24gb_ram():
    result = _get_viable_models(ram_gb=24.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:31b" in tags


def test_models_constant_has_required_fields():
    for model in MODELS:
        assert "tag" in model
        assert "min_ram_gb" in model
        assert "max_ctx" in model
        assert "audio" in model


# --- FakeSystemService ---

def test_fake_check_returns_expected_keys():
    svc = FakeSystemService()
    result = svc.check()
    assert "ram_gb" in result
    assert "disk_free_gb" in result
    assert "gpu" in result
    assert "ollama_running" in result
    assert "viable_models" in result


def test_fake_check_default_values():
    svc = FakeSystemService()
    result = svc.check()
    assert result["ram_gb"] == 8.0
    assert result["disk_free_gb"] == 50.0
    assert result["gpu"]["available"] is False
    assert result["ollama_running"] is True


def test_fake_check_low_ram(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SYSTEM_RAM_GB", "3.0")
    svc = FakeSystemService()
    result = svc.check()
    assert result["ram_gb"] == 3.0
    assert result["viable_models"] == []


def test_fake_check_with_gpu(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SYSTEM_GPU", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM_GPU_VRAM", "16.0")
    svc = FakeSystemService()
    result = svc.check()
    assert result["gpu"]["available"] is True
    assert result["gpu"]["vram_gb"] == 16.0


def test_fake_check_ollama_not_running(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SYSTEM_OLLAMA_RUNNING", "0")
    svc = FakeSystemService()
    result = svc.check()
    assert result["ollama_running"] is False


# --- get_system_service factory ---

def test_get_system_service_returns_real_by_default(monkeypatch):
    monkeypatch.delenv("TROVE_FAKE_SYSTEM", raising=False)
    svc = get_system_service()
    assert isinstance(svc, RealSystemService)


def test_get_system_service_returns_fake_when_env_set(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    svc = get_system_service()
    assert isinstance(svc, FakeSystemService)
