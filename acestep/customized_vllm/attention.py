"""Attention module with paged KV cache, Flash Attention and SDPA fallback."""

import torch
from torch import nn
import torch.nn.functional as F

from acestep.customized_vllm.context import get_context

_HAS_TRITON = False
_HAS_FLASH_ATTN = False

try:
    import triton
    import triton.language as tl
    _HAS_TRITON = True
except ImportError:
    pass

try:
    from flash_attn import flash_attn_varlen_func, flash_attn_with_kvcache
    _HAS_FLASH_ATTN = True
except ImportError:
    pass


# -- Triton KV cache store kernel (fast path) --

if _HAS_TRITON:
    @triton.jit
    def _store_kvcache_triton(
        key_ptr, key_stride, value_ptr, value_stride,
        k_cache_ptr, v_cache_ptr, slot_mapping_ptr, D: tl.constexpr,
    ):
        idx = tl.program_id(0)
        slot = tl.load(slot_mapping_ptr + idx)
        if slot == -1:
            return
        offs = tl.arange(0, D)
        tl.store(k_cache_ptr + slot * D + offs, tl.load(key_ptr + idx * key_stride + offs))
        tl.store(v_cache_ptr + slot * D + offs, tl.load(value_ptr + idx * value_stride + offs))


def _store_kvcache_pytorch(key, value, k_cache, v_cache, slot_mapping):
    """Pure PyTorch fallback for KV cache store."""
    N, num_kv_heads, head_dim = key.shape
    D = num_kv_heads * head_dim
    valid = slot_mapping != -1
    slots = slot_mapping[valid]
    k_cache.reshape(-1, D)[slots] = key.reshape(N, D)[valid]
    v_cache.reshape(-1, D)[slots] = value.reshape(N, D)[valid]


def store_kvcache(key, value, k_cache, v_cache, slot_mapping):
    """Store key/value into paged KV cache."""
    if _HAS_TRITON:
        N, num_heads, head_dim = key.shape
        D = num_heads * head_dim
        _store_kvcache_triton[(N,)](
            key, key.stride(0), value, value.stride(0),
            k_cache, v_cache, slot_mapping, D,
        )
    else:
        _store_kvcache_pytorch(key, value, k_cache, v_cache, slot_mapping)


# -- SDPA fallback implementations --

def _sdpa_varlen_prefill(q, k, v, cu_seqlens_q, cu_seqlens_k, scale, num_heads, num_kv_heads):
    """SDPA prefill: per-sequence causal attention on packed sequences."""
    outputs = []
    enable_gqa = num_heads != num_kv_heads
    for i in range(cu_seqlens_q.shape[0] - 1):
        qs, qe = cu_seqlens_q[i].item(), cu_seqlens_q[i + 1].item()
        ks, ke = cu_seqlens_k[i].item(), cu_seqlens_k[i + 1].item()
        qi = q[qs:qe].unsqueeze(0).transpose(1, 2)
        ki = k[ks:ke].unsqueeze(0).transpose(1, 2)
        vi = v[ks:ke].unsqueeze(0).transpose(1, 2)
        oi = F.scaled_dot_product_attention(qi, ki, vi, scale=scale, is_causal=True, enable_gqa=enable_gqa)
        outputs.append(oi.transpose(1, 2).squeeze(0))
    return torch.cat(outputs, dim=0)


def _sdpa_decode_paged(q, k_cache, v_cache, context_lens, block_tables, scale, num_heads, num_kv_heads):
    """SDPA decode: single query token against paged KV cache per sequence."""
    block_size = k_cache.shape[1]
    outputs = []
    enable_gqa = num_heads != num_kv_heads
    for i in range(q.shape[0]):
        ctx_len = context_lens[i].item()
        n_blocks = (ctx_len + block_size - 1) // block_size
        indices = block_tables[i, :n_blocks]
        ki = k_cache[indices].reshape(-1, num_kv_heads, k_cache.shape[-1])[:ctx_len]
        vi = v_cache[indices].reshape(-1, num_kv_heads, v_cache.shape[-1])[:ctx_len]
        qi = q[i].unsqueeze(0).transpose(1, 2)
        ki = ki.unsqueeze(0).transpose(1, 2)
        vi = vi.unsqueeze(0).transpose(1, 2)
        oi = F.scaled_dot_product_attention(qi, ki, vi, scale=scale, is_causal=False, enable_gqa=enable_gqa)
        outputs.append(oi.transpose(1, 2).squeeze(0))
    return torch.stack(outputs, dim=0)


# -- Attention module --

class Attention(nn.Module):
    """Multi-head attention with paged KV cache support."""

    def __init__(self, num_heads, head_dim, scale, num_kv_heads):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.scale = scale
        self.num_kv_heads = num_kv_heads
        self.k_cache = self.v_cache = torch.tensor([])

    def forward(self, q, k, v):
        ctx = get_context()
        k_cache, v_cache = self.k_cache, self.v_cache

        if k_cache.numel() and v_cache.numel():
            store_kvcache(k, v, k_cache, v_cache, ctx.slot_mapping)

        if _HAS_FLASH_ATTN:
            return self._flash_forward(q, k, v, k_cache, v_cache, ctx)
        return self._sdpa_forward(q, k, v, k_cache, v_cache, ctx)

    def _flash_forward(self, q, k, v, k_cache, v_cache, ctx):
        if ctx.is_prefill:
            return flash_attn_varlen_func(
                q, k, v,
                cu_seqlens_q=ctx.cu_seqlens_q, cu_seqlens_k=ctx.cu_seqlens_k,
                max_seqlen_q=ctx.max_seqlen_q, max_seqlen_k=ctx.max_seqlen_k,
                softmax_scale=self.scale, causal=True,
            )
        return flash_attn_with_kvcache(
            q.unsqueeze(1), k_cache, v_cache,
            cache_seqlens=ctx.context_lens, block_table=ctx.block_tables,
            softmax_scale=self.scale, causal=True,
        )

    def _sdpa_forward(self, q, k, v, k_cache, v_cache, ctx):
        if ctx.is_prefill:
            return _sdpa_varlen_prefill(
                q, k, v, ctx.cu_seqlens_q, ctx.cu_seqlens_k,
                self.scale, self.num_heads, self.num_kv_heads,
            )
        return _sdpa_decode_paged(
            q.unsqueeze(1), k_cache, v_cache,
            ctx.context_lens, ctx.block_tables,
            self.scale, self.num_heads, self.num_kv_heads,
        )
