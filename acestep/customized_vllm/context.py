"""Thread-local attention context for passing metadata between engine and layers."""

from dataclasses import dataclass
import threading
import torch


@dataclass
class Context:
    """Holds attention metadata (prefill/decode mode, sequence lengths, KV cache mapping)."""
    is_prefill: bool = False
    cu_seqlens_q: torch.Tensor | None = None
    cu_seqlens_k: torch.Tensor | None = None
    max_seqlen_q: int = 0
    max_seqlen_k: int = 0
    slot_mapping: torch.Tensor | None = None
    context_lens: torch.Tensor | None = None
    block_tables: torch.Tensor | None = None


_THREAD_LOCAL = threading.local()


def get_context() -> Context:
    """Get the current thread's attention context."""
    ctx = getattr(_THREAD_LOCAL, "context", None)
    if ctx is None:
        ctx = Context()
        _THREAD_LOCAL.context = ctx
    return ctx


def set_context(is_prefill, cu_seqlens_q=None, cu_seqlens_k=None,
                max_seqlen_q=0, max_seqlen_k=0, slot_mapping=None,
                context_lens=None, block_tables=None):
    """Set attention context for the current thread."""
    _THREAD_LOCAL.context = Context(
        is_prefill, cu_seqlens_q, cu_seqlens_k,
        max_seqlen_q, max_seqlen_k, slot_mapping, context_lens, block_tables,
    )


def reset_context():
    """Reset attention context to defaults (called after each forward pass)."""
    _THREAD_LOCAL.context = Context()
