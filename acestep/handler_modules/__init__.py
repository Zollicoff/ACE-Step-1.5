"""
Handler utility modules for ACE-Step.

This package contains utility modules extracted from the monolithic handler.py:

- audio_utils: Audio processing utilities (silence detection, normalization, etc.)
- metadata_builder: Metadata construction and parsing

These modules are part of the ongoing refactoring effort to decompose the
large handler.py file into manageable, single-responsibility modules.

See docs/REFACTORING_PLAN.md for the complete refactoring roadmap.
"""

from acestep.handler_modules import audio_utils
from acestep.handler_modules import metadata_builder

__all__ = ["audio_utils", "metadata_builder"]
