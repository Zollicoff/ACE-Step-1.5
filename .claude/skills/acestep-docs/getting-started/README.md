# ACE-Step Installation Guide

## Requirements

- Python 3.11
- CUDA GPU recommended (works on CPU/MPS but slower)

## Installation

### Windows Portable Package (Recommended for Windows)

1. Download and extract: [ACE-Step-1.5.7z](https://files.acemusic.ai/acemusic/win/ACE-Step-1.5.7z)
2. Requirements: CUDA 12.8

**Launch:**
```bash
# Gradio Web UI
python_embeded\python -m acestep.entry.gradio_app

# REST API Server
python_embeded\python -m acestep.entry.api_server
```

### Standard Installation (All Platforms)

**1. Install uv (Package Manager)**
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Clone & Install**
```bash
git clone https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5
uv sync
```

**3. Launch**
```bash
# Gradio Web UI (http://localhost:7860)
uv run acestep

# REST API Server (http://localhost:8001)
uv run acestep-api
```

## Model Download

Models are automatically downloaded on first run. Manual download options:

```bash
# Download main model
uv run acestep-download

# Download all models
uv run acestep-download --all

# List available models
uv run acestep-download --list
```

### GPU VRAM Recommendations

| GPU VRAM | Recommended LM Model | Notes |
|----------|---------------------|-------|
| ≤6GB | None (DiT only) | LM disabled to save memory |
| 6-12GB | `acestep-5Hz-lm-0.6B` | Lightweight, good balance |
| 12-16GB | `acestep-5Hz-lm-1.7B` | Better quality |
| ≥16GB | `acestep-5Hz-lm-4B` | Best quality |

## Command Line Options

### Gradio UI (`acestep`)

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 7860 | Server port |
| `--server-name` | 127.0.0.1 | Server address (`0.0.0.0` for network) |
| `--share` | false | Create public Gradio link |
| `--language` | en | UI language: `en`, `zh`, `ja` |
| `--init_service` | false | Auto-initialize models on startup |
| `--config_path` | auto | DiT model name |
| `--lm_model_path` | auto | LM model name |
| `--offload_to_cpu` | auto | CPU offload (auto if VRAM < 16GB) |
| `--enable-api` | false | Enable REST API endpoints |
| `--api-key` | none | API authentication key |

**Examples:**
```bash
# Public access with Chinese UI
uv run acestep --server-name 0.0.0.0 --share --language zh

# Pre-initialize models
uv run acestep --init_service true --config_path acestep-v15-turbo

# Enable API with authentication
uv run acestep --enable-api --api-key sk-your-secret-key
```

### REST API Server (`acestep-api`)

Same options as Gradio UI. See [API documentation](../api/API.md) for endpoints.
