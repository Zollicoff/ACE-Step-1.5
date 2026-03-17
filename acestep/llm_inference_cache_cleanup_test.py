"""Unit tests for accelerator cache cleanup in ``LLMHandler``."""

import unittest
from unittest.mock import patch

try:
    from acestep.llm_inference import LLMHandler
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - dependency guard
    LLMHandler = None
    _IMPORT_ERROR = exc


@unittest.skipIf(LLMHandler is None, f"llm_inference import unavailable: {_IMPORT_ERROR}")
class LlmAcceleratorCacheCleanupTests(unittest.TestCase):
    """Verify _clear_accelerator_cache handles each backend correctly."""

    def test_clears_cuda_cache_when_available(self):
        """CUDA cache should be emptied when CUDA is available."""
        handler = LLMHandler()
        with patch("torch.cuda.is_available", return_value=True), \
             patch("torch.cuda.empty_cache") as cuda_mock:
            handler._clear_accelerator_cache()
        cuda_mock.assert_called_once()

    def test_clears_xpu_cache_when_available(self):
        """XPU cache should be emptied when XPU is available."""
        handler = LLMHandler()
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.xpu.is_available", return_value=True, create=True), \
             patch("torch.xpu.empty_cache", create=True) as xpu_mock:
            handler._clear_accelerator_cache()
        xpu_mock.assert_called_once()

    def test_clears_mps_cache_when_available(self):
        """MPS cache should be emptied when MPS is available."""
        handler = LLMHandler()
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.backends.mps.is_available", return_value=True), \
             patch("torch.mps.empty_cache", create=True) as mps_mock:
            handler._clear_accelerator_cache()
        mps_mock.assert_called_once()

    def test_noop_when_no_accelerator_available(self):
        """Method should be a safe no-op when no accelerator is present."""
        handler = LLMHandler()
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.backends.mps.is_available", return_value=False), \
             patch("torch.cuda.empty_cache") as cuda_mock:
            handler._clear_accelerator_cache()
        cuda_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
