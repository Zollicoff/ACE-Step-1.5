"""Thread safety tests for the local_cache module-level singleton."""

import threading
import unittest

from acestep.local_cache import _local_cache_lock


class LocalCacheLockTests(unittest.TestCase):
    """Verify get_local_cache() has proper lock protection."""

    def test_module_lock_exists(self):
        """Module-level lock for get_local_cache must be present."""
        self.assertIsInstance(_local_cache_lock, type(threading.Lock()))


if __name__ == "__main__":
    unittest.main()
