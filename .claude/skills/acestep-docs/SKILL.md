---
name: acestep-docs
description: ACE-Step documentation and troubleshooting. Use when users ask about installing ACE-Step, GPU configuration, model download, Gradio UI usage, API integration, or troubleshooting issues like VRAM problems, CUDA errors, or model loading failures.
allowed-tools: Read, Glob, Grep
---

# ACE-Step Documentation

Documentation skill for ACE-Step music generation system.

## Quick Reference

### Getting Started
| Document | Description |
|----------|-------------|
| [README.md](getting-started/README.md) | Installation, model download, startup commands |
| [Tutorial.md](getting-started/Tutorial.md) | Getting started tutorial, best practices |
| [ABOUT.md](getting-started/ABOUT.md) | Project overview, architecture, model zoo |

### Guides
| Document | Description |
|----------|-------------|
| [GRADIO_GUIDE.md](guides/GRADIO_GUIDE.md) | Web UI usage guide |
| [INFERENCE.md](guides/INFERENCE.md) | Inference parameters tuning |
| [GPU_COMPATIBILITY.md](guides/GPU_COMPATIBILITY.md) | GPU/VRAM configuration, hardware recommendations |

### API (for developers)
| Document | Description |
|----------|-------------|
| [API.md](api/API.md) | REST API documentation |
| [Openrouter_API.md](api/Openrouter_API.md) | OpenRouter API integration |

## Instructions

1. Installation questions → read [getting-started/README.md](getting-started/README.md)
2. General usage / best practices → read [getting-started/Tutorial.md](getting-started/Tutorial.md)
3. Project overview / architecture → read [getting-started/ABOUT.md](getting-started/ABOUT.md)
4. Web UI questions → read [guides/GRADIO_GUIDE.md](guides/GRADIO_GUIDE.md)
5. Inference parameter tuning → read [guides/INFERENCE.md](guides/INFERENCE.md)
6. GPU/VRAM issues → read [guides/GPU_COMPATIBILITY.md](guides/GPU_COMPATIBILITY.md)
7. API development → read [api/API.md](api/API.md) or [api/Openrouter_API.md](api/Openrouter_API.md)

## Common Issues

- **Installation problems**: See getting-started/README.md
- **VRAM insufficient**: See guides/GPU_COMPATIBILITY.md
- **Model download failed**: See getting-started/README.md
- **Inference quality issues**: See guides/INFERENCE.md
- **Gradio UI not starting**: See guides/GRADIO_GUIDE.md
