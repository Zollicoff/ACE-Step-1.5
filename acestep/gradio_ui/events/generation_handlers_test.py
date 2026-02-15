"""Unit tests for generation input event handlers."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from acestep.gradio_ui.events import generation_handlers
    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependency guard
    generation_handlers = None
    _IMPORT_ERROR = exc


class _FakeDitHandler:
    """Minimal DiT handler stub for analyze-src-audio tests."""

    def __init__(self, convert_result):
        self._convert_result = convert_result

    def convert_src_audio_to_codes(self, _src_audio):
        """Return configured conversion output."""
        return self._convert_result


@unittest.skipIf(generation_handlers is None, f"generation_handlers import unavailable: {_IMPORT_ERROR}")
class GenerationHandlersTests(unittest.TestCase):
    """Tests for source-audio analysis validation behavior."""

    @patch("acestep.gradio_ui.events.generation_handlers.gr.Warning")
    @patch("acestep.gradio_ui.events.generation_handlers.understand_music")
    def test_analyze_src_audio_rejects_non_audio_code_output(
        self,
        understand_music_mock,
        warning_mock,
    ):
        """Reject conversion output that has no serialized audio-code tokens."""
        dit_handler = _FakeDitHandler("ERROR: not an audio file")
        llm_handler = SimpleNamespace(llm_initialized=True)

        result = generation_handlers.analyze_src_audio(
            dit_handler=dit_handler,
            llm_handler=llm_handler,
            src_audio="fake.mp3",
            constrained_decoding_debug=False,
        )

        self.assertEqual(result, ("", "", "", "", None, None, "", "", "", False))
        understand_music_mock.assert_not_called()
        warning_mock.assert_called_once()

    @patch("acestep.gradio_ui.events.generation_handlers.gr.Warning")
    @patch("acestep.gradio_ui.events.generation_handlers.understand_music")
    def test_analyze_src_audio_allows_valid_audio_code_output(
        self,
        understand_music_mock,
        warning_mock,
    ):
        """Pass valid audio codes through to LM understanding."""
        dit_handler = _FakeDitHandler("<|audio_code_123|><|audio_code_456|>")
        llm_handler = SimpleNamespace(llm_initialized=True)
        understand_music_mock.return_value = SimpleNamespace(
            success=True,
            status_message="ok",
            caption="caption",
            lyrics="lyrics",
            bpm=120,
            duration=30.0,
            keyscale="C major",
            language="en",
            timesignature="4",
        )

        result = generation_handlers.analyze_src_audio(
            dit_handler=dit_handler,
            llm_handler=llm_handler,
            src_audio="real.mp3",
            constrained_decoding_debug=False,
        )

        self.assertEqual(result[0], "<|audio_code_123|><|audio_code_456|>")
        self.assertEqual(result[1], "ok")
        understand_music_mock.assert_called_once()
        warning_mock.assert_not_called()


@unittest.skipIf(generation_handlers is None, f"generation_handlers import unavailable: {_IMPORT_ERROR}")
class AutoCheckboxTests(unittest.TestCase):
    """Tests for optional-parameter Auto checkbox handler functions."""

    def test_on_auto_checkbox_change_checked_returns_default_and_non_interactive(self):
        """When Auto is checked, field should reset to default and become non-interactive."""
        result = generation_handlers.on_auto_checkbox_change(True, "bpm")
        # gr.update returns a dict-like object; check value and interactive
        self.assertIsNone(result["value"])
        self.assertFalse(result["interactive"])

    def test_on_auto_checkbox_change_unchecked_returns_interactive(self):
        """When Auto is unchecked, field should become interactive (no value reset)."""
        result = generation_handlers.on_auto_checkbox_change(False, "bpm")
        self.assertTrue(result["interactive"])

    def test_on_auto_checkbox_change_all_fields(self):
        """All supported field names should produce valid defaults when checked."""
        expected = {
            "bpm": None,
            "key_scale": "",
            "time_signature": "",
            "vocal_language": "unknown",
            "audio_duration": -1,
        }
        for field_name, expected_value in expected.items():
            result = generation_handlers.on_auto_checkbox_change(True, field_name)
            self.assertEqual(result["value"], expected_value, f"Field {field_name}")
            self.assertFalse(result["interactive"], f"Field {field_name}")

    def test_reset_all_auto_returns_correct_count(self):
        """reset_all_auto should return exactly 10 gr.update objects."""
        result = generation_handlers.reset_all_auto()
        self.assertEqual(len(result), 10)

    def test_reset_all_auto_checkboxes_are_true(self):
        """First 5 outputs (auto checkboxes) should all be set to True."""
        result = generation_handlers.reset_all_auto()
        for i in range(5):
            self.assertTrue(result[i]["value"], f"Auto checkbox at index {i}")

    def test_reset_all_auto_fields_are_defaults(self):
        """Last 5 outputs (fields) should be reset to auto defaults."""
        result = generation_handlers.reset_all_auto()
        self.assertIsNone(result[5]["value"])         # bpm
        self.assertEqual(result[6]["value"], "")       # key_scale
        self.assertEqual(result[7]["value"], "")       # time_signature
        self.assertEqual(result[8]["value"], "unknown") # vocal_language
        self.assertEqual(result[9]["value"], -1)       # audio_duration

    def test_uncheck_auto_for_populated_fields_all_default(self):
        """When all fields have default values, all auto checkboxes should stay checked."""
        result = generation_handlers.uncheck_auto_for_populated_fields(
            bpm=None, key_scale="", time_signature="",
            vocal_language="unknown", audio_duration=-1,
        )
        self.assertEqual(len(result), 10)
        # Auto checkboxes should be True (checked)
        for i in range(5):
            self.assertTrue(result[i]["value"], f"Auto checkbox at index {i}")
        # Fields should be non-interactive
        for i in range(5, 10):
            self.assertFalse(result[i]["interactive"], f"Field at index {i}")

    def test_uncheck_auto_for_populated_fields_all_populated(self):
        """When all fields have non-default values, all auto checkboxes should be unchecked."""
        result = generation_handlers.uncheck_auto_for_populated_fields(
            bpm=120, key_scale="C major", time_signature="4",
            vocal_language="en", audio_duration=30.0,
        )
        # Auto checkboxes should be False (unchecked)
        for i in range(5):
            self.assertFalse(result[i]["value"], f"Auto checkbox at index {i}")
        # Fields should be interactive
        for i in range(5, 10):
            self.assertTrue(result[i]["interactive"], f"Field at index {i}")

    def test_uncheck_auto_for_populated_fields_mixed(self):
        """Mixed populated/default fields should only uncheck populated ones."""
        result = generation_handlers.uncheck_auto_for_populated_fields(
            bpm=120, key_scale="", time_signature="4",
            vocal_language="unknown", audio_duration=-1,
        )
        self.assertFalse(result[0]["value"])   # bpm_auto unchecked
        self.assertTrue(result[1]["value"])    # key_auto stays checked
        self.assertFalse(result[2]["value"])   # timesig_auto unchecked
        self.assertTrue(result[3]["value"])    # vocal_lang_auto stays checked
        self.assertTrue(result[4]["value"])    # duration_auto stays checked


if __name__ == "__main__":
    unittest.main()
