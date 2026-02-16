"""Tests for path-sanitisation helpers in data_module.

Covers the _resolve_and_validate_dir and _safe_child_path functions
that guard against path-traversal attacks (CodeQL: uncontrolled data
used in path expression).
"""

import os
import json
import tempfile
import unittest

from acestep.training.data_module import (
    _resolve_and_validate_dir,
    _safe_child_path,
    PreprocessedTensorDataset,
    load_dataset_from_json,
)


class ResolveAndValidateDirTests(unittest.TestCase):
    """Tests for _resolve_and_validate_dir."""

    def test_valid_directory(self):
        with tempfile.TemporaryDirectory() as d:
            result = _resolve_and_validate_dir(d)
            self.assertEqual(result, os.path.realpath(d))

    def test_nonexistent_directory_raises(self):
        with self.assertRaises(ValueError):
            _resolve_and_validate_dir("/nonexistent_path_abc123")

    def test_file_path_raises(self):
        with tempfile.NamedTemporaryFile() as f:
            with self.assertRaises(ValueError):
                _resolve_and_validate_dir(f.name)


class SafeChildPathTests(unittest.TestCase):
    """Tests for _safe_child_path."""

    def test_normal_child(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.realpath(d)
            result = _safe_child_path(base, "foo.pt")
            self.assertEqual(result, os.path.join(base, "foo.pt"))

    def test_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.realpath(d)
            result = _safe_child_path(base, "../../etc/passwd")
            self.assertIsNone(result)

    def test_absolute_path_outside_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.realpath(d)
            result = _safe_child_path(base, "/etc/passwd")
            self.assertIsNone(result)

    def test_absolute_path_inside_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.realpath(d)
            child = os.path.join(base, "sub", "file.pt")
            result = _safe_child_path(base, child)
            self.assertEqual(result, child)


class PreprocessedTensorDatasetPathSafetyTests(unittest.TestCase):
    """Tests that PreprocessedTensorDataset rejects traversal paths."""

    def test_manifest_traversal_paths_skipped(self):
        """Paths in manifest.json that escape tensor_dir are ignored."""
        with tempfile.TemporaryDirectory() as d:
            # Create a manifest with one good and one bad path
            good_pt = os.path.join(d, "good.pt")
            open(good_pt, "wb").close()  # touch

            manifest = {
                "samples": [
                    "good.pt",
                    "../../etc/passwd",
                ]
            }
            with open(os.path.join(d, "manifest.json"), "w") as f:
                json.dump(manifest, f)

            ds = PreprocessedTensorDataset(d)
            # Only the safe path should survive
            self.assertEqual(len(ds.valid_paths), 1)
            self.assertTrue(ds.valid_paths[0].endswith("good.pt"))

    def test_fallback_scan_only_finds_pt_files(self):
        """Without manifest, only .pt files inside tensor_dir are found."""
        with tempfile.TemporaryDirectory() as d:
            for name in ["a.pt", "b.pt", "c.txt"]:
                open(os.path.join(d, name), "wb").close()

            ds = PreprocessedTensorDataset(d)
            self.assertEqual(len(ds.valid_paths), 2)

    def test_nonexistent_dir_raises(self):
        with self.assertRaises(ValueError):
            PreprocessedTensorDataset("/nonexistent_xyz_12345")


class LoadDatasetFromJsonTests(unittest.TestCase):
    """Tests for load_dataset_from_json path validation."""

    def test_nonexistent_file_raises(self):
        with self.assertRaises(ValueError):
            load_dataset_from_json("/nonexistent_file.json")

    def test_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"metadata": {"v": 1}, "samples": [{"a": 1}]}, f)
            path = f.name
        try:
            samples, meta = load_dataset_from_json(path)
            self.assertEqual(len(samples), 1)
            self.assertEqual(meta["v"], 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
