"""Core neural network layers: RMSNorm, rotary embeddings, SiLU activation."""

from functools import lru_cache
import torch
from torch import nn
import torch.nn.functional as F


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization with optional fused residual add."""

    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(hidden_size))

    @torch.compile
    def _norm(self, x):
        orig_dtype = x.dtype
        x = x.float()
        x.mul_(torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps))
        return x.to(orig_dtype).mul_(self.weight)

    @torch.compile
    def _add_norm(self, x, residual):
        orig_dtype = x.dtype
        x = x.float().add_(residual.float())
        residual = x.to(orig_dtype)
        x.mul_(torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps))
        return x.to(orig_dtype).mul_(self.weight), residual

    def forward(self, x, residual=None):
        if residual is None:
            return self._norm(x)
        return self._add_norm(x, residual)


def _apply_rotary_emb(x, cos, sin):
    x1, x2 = torch.chunk(x.float(), 2, dim=-1)
    return torch.cat((x1 * cos - x2 * sin, x2 * cos + x1 * sin), dim=-1).to(x.dtype)


class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE)."""

    def __init__(self, head_size: int, max_position: int, base: float):
        super().__init__()
        inv_freq = 1.0 / (base ** (torch.arange(0, head_size, 2, dtype=torch.float) / head_size))
        freqs = torch.einsum("i,j->ij", torch.arange(max_position, dtype=torch.float), inv_freq)
        cache = torch.cat((freqs.cos(), freqs.sin()), dim=-1).unsqueeze_(1)
        self.register_buffer("cos_sin_cache", cache, persistent=False)

    @torch.compile
    def forward(self, positions, query, key):
        cos_sin = self.cos_sin_cache[positions]
        cos, sin = cos_sin.chunk(2, dim=-1)
        return _apply_rotary_emb(query, cos, sin), _apply_rotary_emb(key, cos, sin)


@lru_cache(1)
def get_rope(head_size: int, max_position: int, base: float):
    """Get or create a cached RotaryEmbedding instance."""
    return RotaryEmbedding(head_size, max_position, base)


class SiluAndMul(nn.Module):
    """SiLU-gated activation: SiLU(x) * y where [x, y] = chunk(input, 2)."""

    @torch.compile
    def forward(self, x):
        x, y = x.chunk(2, -1)
        return F.silu(x) * y
