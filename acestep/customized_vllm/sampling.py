"""Sampling parameters and token sampler for LLM inference."""

from dataclasses import dataclass, field
from typing import Optional, Callable, Any

import torch
from torch import nn


@dataclass
class SamplingParams:
    """Configuration for token sampling during generation."""
    temperature: float = 1.0
    max_tokens: int = 64
    ignore_eos: bool = False
    cfg_scale: float = 1.0
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    repetition_penalty: float = 1.0
    logits_processor: Optional[Any] = field(default=None, repr=False)
    logits_processor_update_state: Optional[Callable[[int], None]] = field(default=None, repr=False)

    def __post_init__(self):
        assert self.temperature > 1e-10, "greedy sampling is not permitted"
        assert self.cfg_scale >= 1.0, "cfg_scale must be >= 1.0"
        if self.top_k is not None:
            assert self.top_k > 0, "top_k must be > 0"
        if self.top_p is not None:
            assert 0.0 < self.top_p <= 1.0, "top_p must be in (0.0, 1.0]"
        assert self.repetition_penalty > 0.0, "repetition_penalty must be > 0.0"


def _apply_top_k_top_p(logits, k, p):
    """Apply top-k and/or top-p filtering to logits in-place."""
    if p is None and k is None:
        return logits
    if p is None:
        return _apply_top_k_only(logits, k)

    logits_sort, logits_idx = logits.sort(dim=-1, descending=False)
    if k is not None:
        vocab_size = logits_sort.size(1)
        k_clamped = k.clamp(1, vocab_size).long()
        thresh = logits_sort.gather(1, (vocab_size - k_clamped).unsqueeze(1))
        logits_sort.masked_fill_(logits_sort < thresh, float("-inf"))

    probs_sum = logits_sort.softmax(dim=-1).cumsum_(dim=-1)
    top_p_mask = probs_sum <= (1.0 - p.unsqueeze(1))
    top_p_mask[:, -1] = False
    logits_sort.masked_fill_(top_p_mask, float("-inf"))
    logits.scatter_(dim=-1, index=logits_idx, src=logits_sort)
    return logits


def _apply_top_k_only(logits, k):
    """Fast top-k filtering without full sort."""
    vocab_size = logits.shape[1]
    no_filter = (k <= 0) | (k >= vocab_size)
    k_safe = k.masked_fill(no_filter, 1).long()
    max_k = int(k_safe.max().clamp(max=vocab_size))
    topk_vals = logits.topk(max_k, dim=1).values
    thresh = topk_vals.gather(1, (k_safe - 1).clamp(0, max_k - 1).unsqueeze(1))
    thresh.masked_fill_(no_filter.unsqueeze(1), float("-inf"))
    logits.masked_fill_(logits < thresh, float("-inf"))
    return logits


class Sampler(nn.Module):
    """Token sampler with temperature scaling and top-k/top-p filtering."""

    @torch.compile
    def forward(self, logits, temperatures, top_ks=None, top_ps=None):
        """Sample one token per sequence from logits."""
        logits = logits.float().div_(temperatures.unsqueeze(1))
        _apply_top_k_top_p(logits, top_ks, top_ps)
        probs = torch.softmax(logits, dim=-1)
        return probs.div_(torch.empty_like(probs).exponential_(1).clamp_min_(1e-10)).argmax(dim=-1)
