import pytest
from unittest.mock import MagicMock, patch

from backend.system.service import (
    MODELS,
    get_disk_free_gb,
    get_gpu_info,
    get_ram_gb,
    get_viable_models,
)


def test_get_ram_gb_returns_positive_float():
    result = get_ram_gb()
    assert isinstance(result, float)
    assert result > 0


def test_get_disk_free_gb_returns_non_negative_float():
    result = get_disk_free_gb()
    assert isinstance(result, float)
    assert result >= 0


def test_get_gpu_info_no_nvidia():
    with patch("backend.system.service.shutil.which", return_value=None):
        result = get_gpu_info()
    assert result["available"] is False
    assert result["vram_gb"] is None


def test_get_gpu_info_nvidia_present():
    mock_result = MagicMock(returncode=0, stdout="8192\n")
    with patch("backend.system.service.shutil.which", return_value="/usr/bin/nvidia-smi"):
        with patch("backend.system.service.subprocess.run", return_value=mock_result):
            result = get_gpu_info()
    assert result["available"] is True
    assert result["vram_gb"] == pytest.approx(8.0, abs=0.1)


def test_get_viable_models_3gb_ram():
    result = get_viable_models(ram_gb=3.0, gpu_info={"available": False, "vram_gb": None})
    assert result == []


def test_get_viable_models_6gb_ram():
    result = get_viable_models(ram_gb=6.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:e4b" in tags
    assert "gemma4:31b" not in tags


def test_get_viable_models_24gb_ram():
    result = get_viable_models(ram_gb=24.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:31b" in tags


def test_models_constant_has_required_fields():
    for model in MODELS:
        assert "tag" in model
        assert "min_ram_gb" in model
        assert "max_ctx" in model
        assert "audio" in model
