# Float32 Matmul Precision Configuration

## Overview

This feature adds user-configurable control for PyTorch's float32 matrix multiplication precision via `torch.set_float32_matmul_precision()`. This setting controls the TF32 (TensorFloat-32) speed/accuracy trade-off on Ampere+ GPUs (RTX 30/40 series, A100, etc.).

## Usage

### UI Control

A new dropdown control has been added to the Service Configuration section:

**Float32 Matmul Precision**
- `highest` (default): Full IEEE FP32 precision - highest accuracy, slower on Ampere+ GPUs
- `high`: TF32 enabled - faster on Ampere+ GPUs with minimal accuracy loss  
- `medium`: TF32+ enabled - fastest option with more aggressive optimizations

The dropdown appears in the Service Configuration accordion, below the MLX DiT checkbox.

### Environment Variable

You can also set the precision via environment variable before starting the application:

```bash
# Linux/macOS
export ACE_STEP_FLOAT32_MATMUL_PRECISION=high
python cli.py ...

# Windows
set ACE_STEP_FLOAT32_MATMUL_PRECISION=high
python cli.py ...
```

Valid values: `highest`, `high`, `medium` (case-insensitive)

### Configuration File (.env)

Add to your `.env` file:
```
ACE_STEP_FLOAT32_MATMUL_PRECISION=high
```

## Default Behavior

The default setting is `highest`, which preserves the current behavior (full FP32 precision). This ensures backward compatibility and consistent results.

## When to Use Each Setting

### `highest` (default)
- **Use when**: You need maximum accuracy and reproducibility
- **Trade-off**: Slower performance on Ampere+ GPUs
- **Recommended for**: Research, benchmarking, final production runs

### `high` (TF32)
- **Use when**: You want faster inference with minimal quality impact
- **Trade-off**: Slight numerical differences vs. FP32 (typically negligible for music generation)
- **Recommended for**: Most users with RTX 30/40 series or A100+ GPUs

### `medium` (TF32+)
- **Use when**: You need maximum speed and quality loss is acceptable
- **Trade-off**: More aggressive optimizations, potentially more noticeable differences
- **Recommended for**: Rapid experimentation, preview generations

## Technical Details

### What is TF32?

TensorFloat-32 (TF32) is a math mode for NVIDIA Ampere GPUs that:
- Uses FP32 input/output
- Uses reduced precision (19-bit) for internal calculations
- Provides up to 8x speedup for certain operations
- Typically has negligible impact on model quality

### Implementation

The precision is applied early during service initialization in `handler.py`:
1. Before any model loading
2. After device selection
3. Logs the selected precision level

### GPU Compatibility

- **Ampere+ GPUs** (RTX 30/40, A100, etc.): TF32 provides significant speedup
- **Pre-Ampere GPUs** (RTX 20, GTX 10, etc.): Setting has no effect
- **MPS/CPU**: Setting has no effect

## Code Changes Summary

### Modified Files

1. **`acestep/gpu_config.py`**
   - Added `float32_matmul_precision` field to `GPUConfig` dataclass
   - Added `FLOAT32_MATMUL_PRECISION_ENV` environment variable constant
   - Updated `get_gpu_config()` and `get_gpu_config_for_tier()` to include precision setting

2. **`acestep/handler.py`**
   - Added `float32_matmul_precision` parameter to `initialize_service()`
   - Calls `torch.set_float32_matmul_precision()` early in initialization
   - Logs the precision setting

3. **`acestep/gradio_ui/interfaces/generation.py`**
   - Added `float32_matmul_precision_dropdown` UI control
   - Wired to service configuration

4. **`acestep/gradio_ui/events/generation_handlers.py`**
   - Updated `init_service_wrapper()` to accept and pass `float32_matmul_precision`

5. **`acestep/gradio_ui/events/__init__.py`**
   - Connected dropdown to initialization event handler

6. **Translation files** (`en.json`, `zh.json`, `ja.json`, `he.json`)
   - Added `float32_matmul_precision_label` and `float32_matmul_precision_info` translations

## Backward Compatibility

- Default value is `"highest"` which preserves exact current behavior
- All existing code continues to work without changes
- `api_server.py` and `cli.py` use the default value automatically
- Environment variable override works for all entry points

## Testing

To verify the feature is working:

1. Start the application
2. Check logs for: `Set PyTorch float32 matmul precision to 'highest'` (or your selected value)
3. Change the dropdown value in UI
4. Click "Initialize Service"
5. Verify logs show the new precision setting

## References

- PyTorch Documentation: https://pytorch.org/docs/stable/generated/torch.set_float32_matmul_precision.html
- NVIDIA TF32 Details: https://blogs.nvidia.com/blog/2020/05/14/tensorfloat-32-precision-format/
