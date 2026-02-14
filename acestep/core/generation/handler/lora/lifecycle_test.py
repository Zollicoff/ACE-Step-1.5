"""Tests for LoRA/LoKr lifecycle loading behavior."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import torch

from acestep.core.generation.handler.lora import lifecycle


class _DummyDecoder:
    """Minimal decoder stub for lifecycle loader tests."""

    def __init__(self) -> None:
        self._weights = {"w": torch.zeros(1)}

    def state_dict(self):
        """Return a tiny state dict suitable for backup/restore paths."""
        return self._weights

    def load_state_dict(self, state_dict, strict=False):
        """Pretend to restore weights and report no key mismatches."""
        self._weights = state_dict
        return SimpleNamespace(missing_keys=[], unexpected_keys=[])

    def to(self, *_args, **_kwargs):
        """Match torch module ``to`` chaining."""
        return self

    def eval(self):
        """Match torch module ``eval`` API."""
        return self


class _DummyHandler:
    """Handler stub exposing the attributes used by ``load_lora``."""

    def __init__(self) -> None:
        self.model = SimpleNamespace(decoder=_DummyDecoder())
        self.device = "cpu"
        self.dtype = torch.float32
        self.quantization = None
        self._base_decoder = None
        self.lora_loaded = False
        self.use_lora = False
        self.lora_scale = 1.0
        self._lora_active_adapter = None

    def _ensure_lora_registry(self):
        """Satisfy lifecycle hook without side effects."""
        return None

    def _rebuild_lora_registry(self, lora_path=None):
        """Return deterministic empty registry output."""
        _ = lora_path
        return 0, []

    def _debug_lora_registry_snapshot(self):
        """Return simple debug payload."""
        return {}


class LifecycleTests(unittest.TestCase):
    """Coverage for LoKr path detection and load branching."""

    def test_resolve_lokr_weights_from_directory(self):
        """Directory containing ``lokr_weights.safetensors`` should resolve."""
        with tempfile.TemporaryDirectory() as tmp:
            weights = Path(tmp) / lifecycle.LOKR_WEIGHTS_FILENAME
            weights.write_bytes(b"")
            resolved = lifecycle._resolve_lokr_weights_path(str(Path(tmp)))
            self.assertEqual(resolved, str(weights))

    def test_resolve_lokr_weights_from_file(self):
        """Direct ``lokr_weights.safetensors`` file should resolve."""
        with tempfile.TemporaryDirectory() as tmp:
            weights = Path(tmp) / lifecycle.LOKR_WEIGHTS_FILENAME
            weights.write_bytes(b"")
            resolved = lifecycle._resolve_lokr_weights_path(str(weights))
            self.assertEqual(resolved, str(weights))

    def test_load_lora_accepts_lokr_directory_without_adapter_config(self):
        """LoKr directory should bypass PEFT config-file requirement."""
        handler = _DummyHandler()
        with tempfile.TemporaryDirectory() as tmp:
            adapter_dir = Path(tmp) / "adapter"
            adapter_dir.mkdir(parents=True, exist_ok=True)
            weights = adapter_dir / lifecycle.LOKR_WEIGHTS_FILENAME
            weights.write_bytes(b"")
            with patch("acestep.core.generation.handler.lora.lifecycle._load_lokr_adapter") as mock_load_lokr:
                message = lifecycle.load_lora(handler, str(adapter_dir))

        self.assertEqual(message, f"✅ LoKr loaded from {weights}")
        mock_load_lokr.assert_called_once_with(handler.model.decoder, str(weights))

    def test_load_lora_invalid_adapter_message_mentions_lokr(self):
        """Invalid adapter error should mention both LoRA and LoKr expectations."""
        handler = _DummyHandler()
        with tempfile.TemporaryDirectory() as tmp:
            message = lifecycle.load_lora(handler, tmp)
        self.assertIn("adapter_config.json", message)
        self.assertIn(lifecycle.LOKR_WEIGHTS_FILENAME, message)

    def test_load_lokr_adapter_recreates_with_dora_when_weight_decompose_enabled(self):
        """Weight-decompose config should request a second LyCORIS net with DoRA enabled."""
        decoder = _DummyDecoder()
        base_net = Mock()
        dora_net = Mock()
        create_lycoris = Mock(side_effect=[base_net, dora_net])
        fake_lycoris = SimpleNamespace(
            LycorisNetwork=SimpleNamespace(apply_preset=Mock()),
            create_lycoris=create_lycoris,
        )
        config = lifecycle.LoKRConfig(weight_decompose=True)

        with patch.dict("sys.modules", {"lycoris": fake_lycoris}):
            with patch("acestep.core.generation.handler.lora.lifecycle._load_lokr_config", return_value=config):
                result = lifecycle._load_lokr_adapter(decoder, "weights.safetensors")

        self.assertIs(result, dora_net)
        self.assertEqual(create_lycoris.call_count, 2)
        self.assertNotIn("dora_wd", create_lycoris.call_args_list[0].kwargs)
        self.assertTrue(create_lycoris.call_args_list[1].kwargs["dora_wd"])
        dora_net.apply_to.assert_called_once_with()
        dora_net.load_weights.assert_called_once_with("weights.safetensors")
        self.assertIs(decoder._lycoris_net, dora_net)

    def test_load_lokr_adapter_uses_base_net_when_dora_not_supported(self):
        """DoRA create failures should warn and keep the initially created LyCORIS net."""
        decoder = _DummyDecoder()
        base_net = Mock()
        create_lycoris = Mock(side_effect=[base_net, RuntimeError("unsupported")])
        fake_lycoris = SimpleNamespace(
            LycorisNetwork=SimpleNamespace(apply_preset=Mock()),
            create_lycoris=create_lycoris,
        )
        config = lifecycle.LoKRConfig(weight_decompose=True)

        with patch.dict("sys.modules", {"lycoris": fake_lycoris}):
            with patch("acestep.core.generation.handler.lora.lifecycle._load_lokr_config", return_value=config):
                with patch("acestep.core.generation.handler.lora.lifecycle.logger.warning") as mock_warning:
                    result = lifecycle._load_lokr_adapter(decoder, "weights.safetensors")

        self.assertIs(result, base_net)
        self.assertEqual(create_lycoris.call_count, 2)
        mock_warning.assert_called_once()
        base_net.apply_to.assert_called_once_with()
        base_net.load_weights.assert_called_once_with("weights.safetensors")
        self.assertIs(decoder._lycoris_net, base_net)


if __name__ == "__main__":
    unittest.main()
