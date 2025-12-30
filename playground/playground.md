# ACE-Step Playground - Development Specification

## Overview

The Playground is a Gradio-based UI for testing and interacting with the ACE-Step music generation pipeline. It consists of two main sections: **LLM Section** (for generating audio codes) and **ACEStep Section** (for generating audio from codes).

**Key Principles:**
- Keep logic simple - no automatic data flow between sections
- Dynamic UI based on task selection
- Advanced parameters in collapsible panels
- Only modify playground module files, do not touch existing acestep modules

---

## File Structure

```
playground/
├── playground.py           # Entry point
├── playground_handler.py   # Business logic wrapper
├── playground_ui.py        # Gradio UI definition
└── playground.md           # This specification
```

---

## 1. LLM Section

The LLM Section generates audio codes from text descriptions.

### 1.1 Model Loading

| Component | Type | Description |
|-----------|------|-------------|
| `llm_model_dropdown` | Dropdown | Available LLM models from `handler.get_available_llm_models()` |
| `llm_backend` | Dropdown | Options: `["vllm", "pt"]`, default: `"vllm"` |
| `llm_device` | Dropdown | Options: `["auto", "cuda", "cpu"]`, default: `"auto"` |
| `load_llm_btn` | Button | Triggers `handler.initialize_llm()` |
| `llm_status` | Textbox | Displays loading status (read-only) |

**Handler Method:**
```python
handler.initialize_llm(lm_model_path: str, backend: str, device: str) -> str
```

---

### 1.2 Input Panel

#### 1.2.1 Text Inputs (Left Column)

| Component | Type | Description |
|-----------|------|-------------|
| `caption` | Textbox | Music description, multiline (3 lines) |
| `lyrics` | Textbox | Song lyrics, multiline (5 lines) |
| `negative_caption` | Textbox | Negative prompt, default: `"NO USER INPUT"`, multiline (3 lines)|
| `negative_lyrics` | Textbox | Negative prompt, default: `"NO USER INPUT"` , multiline (5 lines)|

remarks：
1. caption and negative_caption use same style
2. lyrics and negative_lyrics use same style


#### 1.2.2 Meta (Right Column - Group)

| Component | Type | Default | Description |
|-----------|------|---------|-------------|
| `bpm` | Number | `None` | Beats per minute |
| `key_scale` | Textbox | `""` | e.g., "C Major", "A minor" |
| `time_signature` | Textbox | `""` | e.g., "4/4", "3/4" |
| `target_duration` | Number | `None` | Target duration in seconds |

#### 1.2.3 Config (Right Column - Group)
Accordion - Collapsed by Default

| Component | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `temperature` | Slider | 0.1 - 2.0 | 0.85 | Sampling temperature |
| `cfg_scale` | Slider | 1.0 - 5.0 | 2.0 | Classifier-free guidance scale |
| `top_k` | Number | None | `None` | Top-K sampling (optional) |
| `top_p` | Slider | 0.0 - 1.0 | 0.9 | Top-P (nucleus) sampling |
| `repetition_penalty` | Slider | 1.0 - 2.0 | 1.0 | Repetition penalty |
| `metadata_temperature` | Slider | 0.1 - 2.0 | 0.85 | Temperature for metadata generation |
| `codes_temperature` | Slider | 0.1 - 2.0 | 1.0 | Temperature for codes generation |

#### 1.2.4 Generate Button

| Component | Type | Description |
|-----------|------|-------------|
| `generate_codes_btn` | Button (primary) | Triggers LLM code generation |

**Handler Method:**
```python
handler.generate_llm_codes(
    caption: str,
    lyrics: str,
    temperature: float,
    cfg_scale: float,
    negative_prompt: str,
    top_k: Optional[int],
    top_p: Optional[float],
    repetition_penalty: float,
    metadata_temperature: float,
    codes_temperature: float,
    target_duration: Optional[float],
    user_metadata: Optional[Dict[str, str]]  # {bpm, keyscale, timesignature}
) -> Tuple[Dict, str, str]  # (metadata, audio_codes, status)
```

---

### 1.3 Results Panel

| Component | Type | Description |
|-----------|------|-------------|
| `metadata_output` | JSON | Generated metadata (read-only) |
| `audio_codes_output` | Textbox | Generated audio codes (multiline, copyable) |
| `llm_generation_status` | Textbox | Generation status message (read-only) |

---

## 2. ACEStep Section

The ACEStep Section generates audio from codes using the DiT model.

### 2.1 Model Loading

| Component | Type | Description |
|-----------|------|-------------|
| `dit_config_dropdown` | Dropdown | Available DiT configs from `handler.get_available_dit_models()` |
| `dit_device` | Dropdown | Options: `["auto", "cuda", "cpu"]`, default: `"auto"` |
| `load_dit_btn` | Button | Triggers `handler.initialize_dit()` |
| `dit_status` | Textbox | Displays loading status (read-only) |

**Handler Method:**
```python
handler.initialize_dit(config_path: str, device: str) -> str
```

---

### 2.2 Task Selection

| Component | Type | Options | Default |
|-----------|------|---------|---------|
| `task_type` | Dropdown | `["generate", "repaint", "cover", "add", "complete", "extract"]` | `"generate"` |

**Task Descriptions:**

| Task | Internal Type | Description | Required Inputs |
|------|---------------|-------------|-----------------|
| `generate` | `text2music` | Generate music from text | caption, lyrics, audio_codes |
| `repaint` | `repaint` | Regenerate a portion of audio | + reference_audio, repaint_start, repaint_end |
| `cover` | `cover` | Create a cover version | + reference_audio, cover_strength |
| `add` | `lego` | Add a track to existing audio | + reference_audio, track_type |
| `complete` | `complete` | Complete partial audio | + reference_audio |
| `extract` | `extract` | Extract audio features | + reference_audio |

---

### 2.3 Logical Conditions (Always Visible)

| Component | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `inference_steps` | Slider | 1 - 100 | 20 | Number of diffusion steps |
| `guidance_scale` | Slider | 1.0 - 20.0 | 7.0 | Classifier-free guidance scale |
| `seed` | Number | - | -1 | Random seed (-1 for random) |
| `use_random_seed` | Checkbox | - | True | Use random seed each time |

---

### 2.4 Model Conditions (Dynamic Based on Task)

#### 2.4.1 Common Inputs (All Tasks)

| Component | Type | Description |
|-----------|------|-------------|
| `ace_caption` | Textbox | Music description (can copy from LLM section) |
| `ace_lyrics` | Textbox | Lyrics (can copy from LLM section) |
| `ace_audio_codes` | Textbox | Audio codes (can copy from LLM section) |

#### 2.4.2 Reference Audio (Tasks: repaint, cover, add, complete, extract)

| Component | Type | Description |
|-----------|------|-------------|
| `reference_audio` | Audio (filepath) | Input audio file |

#### 2.4.3 Repaint Parameters (Task: repaint)

| Component | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `repainting_start` | Number | - | 0.0 | Start time in seconds |
| `repainting_end` | Number | - | 10.0 | End time in seconds |

#### 2.4.4 Cover Parameters (Task: cover)

| Component | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `audio_cover_strength` | Slider | 0.0 - 1.0 | 1.0 | Cover transformation strength |

#### 2.4.5 Track Parameters (Tasks: add, complete)

| Component | Type | Options | Description |
|-----------|------|---------|-------------|
| `track_type` | Dropdown | `["vocal", "bass", "drums", "guitar", "piano", "other"]` | Track to add/complete |

---

### 2.5 Advanced Settings (Accordion - Collapsed by Default)

| Component | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `cfg_interval_start` | Slider | 0.0 - 1.0 | 0.0 | CFG interval start |
| `cfg_interval_end` | Slider | 0.0 - 1.0 | 1.0 | CFG interval end |
| `use_adg` | Checkbox | - | False | Use ADG |
| `audio_format` | Dropdown | `["mp3", "wav", "flac"]` | `"mp3"` | Output audio format |
| `use_tiled_decode` | Checkbox | - | True | Use tiled decoding |
| `vocal_language` | Dropdown | `["en", "zh", "ja", "ko"]` | `"en"` | Vocal language |

---

### 2.6 Generate Button

| Component | Type | Description |
|-----------|------|-------------|
| `generate_audio_btn` | Button (primary) | Triggers audio generation |

**Handler Method:**
```python
handler.generate_audio(
    task_type: str,
    caption: str,
    lyrics: str,
    audio_codes: str,
    inference_steps: int,
    guidance_scale: float,
    seed: int,
    reference_audio_path: Optional[str],
    repainting_start: float,
    repainting_end: float,
    audio_cover_strength: float,
    bpm: Optional[int],
    key_scale: str,
    time_signature: str,
    vocal_language: str,
    use_adg: bool,
    cfg_interval_start: float,
    cfg_interval_end: float,
    audio_format: str,
    use_tiled_decode: bool
) -> Tuple[Optional[str], str]  # (audio_path, status)
```

---

### 2.7 Results Panel

| Component | Type | Description |
|-----------|------|-------------|
| `audio_output` | Audio | Generated audio player |
| `audio_status` | Textbox | Generation status (read-only) |

---

## 3. Dynamic UI Logic

When `task_type` changes, show/hide relevant components:

```python
TASK_VISIBILITY = {
    "generate": {
        "reference_audio": False,
        "repaint_params": False,
        "cover_params": False,
        "track_params": False,
    },
    "repaint": {
        "reference_audio": True,
        "repaint_params": True,
        "cover_params": False,
        "track_params": False,
    },
    "cover": {
        "reference_audio": True,
        "repaint_params": False,
        "cover_params": True,
        "track_params": False,
    },
    "add": {
        "reference_audio": True,
        "repaint_params": False,
        "cover_params": False,
        "track_params": True,
    },
    "complete": {
        "reference_audio": True,
        "repaint_params": False,
        "cover_params": False,
        "track_params": True,
    },
    "extract": {
        "reference_audio": True,
        "repaint_params": False,
        "cover_params": False,
        "track_params": False,
    },
}
```

**Implementation:**
```python
def update_task_visibility(task: str):
    vis = TASK_VISIBILITY[task]
    return (
        gr.update(visible=vis["reference_audio"]),
        gr.update(visible=vis["repaint_params"]),
        gr.update(visible=vis["cover_params"]),
        gr.update(visible=vis["track_params"]),
    )

task_type.change(
    fn=update_task_visibility,
    inputs=[task_type],
    outputs=[reference_audio_group, repaint_group, cover_group, track_group]
)
```

---

## 4. UI Layout Structure

```
gr.Blocks
└── gr.Tabs
    ├── gr.TabItem("LLM Section")
    │   ├── gr.Accordion("1. Model Loading")
    │   │   ├── gr.Row [model_dropdown, backend, device, load_btn]
    │   │   └── status
    │   ├── gr.Accordion("2. Inputs")
    │   │   ├── gr.Row
    │   │   │   ├── gr.Column [caption, lyrics, negative_caption]
    │   │   │   └── gr.Column
    │   │   │       ├── gr.Group("Meta") [bpm, key_scale, time_sig, duration]
    │   │   │       └── gr.Group("Config") [temp, cfg, top_k, top_p, ...]
    │   │   └── generate_codes_btn
    │   └── gr.Accordion("3. Results")
    │       ├── gr.Row [metadata_json, audio_codes_text]
    │       └── status
    │
    └── gr.TabItem("ACEStep Section")
        ├── gr.Accordion("1. Model Loading")
        │   ├── gr.Row [config_dropdown, device, load_btn]
        │   └── status
        ├── gr.Accordion("2. Task & Conditions")
        │   ├── task_type_dropdown
        │   ├── gr.Group("Common Inputs") [caption, lyrics, codes]
        │   ├── gr.Group("Reference Audio", visible=dynamic)
        │   ├── gr.Group("Repaint Params", visible=dynamic)
        │   ├── gr.Group("Cover Params", visible=dynamic)
        │   ├── gr.Group("Track Params", visible=dynamic)
        │   ├── gr.Group("Logical Conditions") [steps, guidance, seed]
        │   └── gr.Accordion("Advanced", open=False) [cfg_interval, adg, format, ...]
        ├── generate_audio_btn
        └── gr.Accordion("3. Results")
            ├── audio_output
            └── status
```

---

## 5. Error Handling

1. **Model Not Loaded**: Check initialization status before generation
2. **Empty Inputs**: Validate required fields before calling handler
3. **Generation Errors**: Display traceback in status textbox

```python
# Example validation
def validate_llm_inputs(caption, lyrics):
    if not caption.strip():
        return None, None, "Error: Caption is required"
    return None  # Continue with generation

# In handler, errors are returned as status string
if not self.llm_handler.llm_initialized:
    return {}, "", "LLM not initialized"
```

---

## 6. Implementation Checklist

- [ ] Update `playground_ui.py` with new layout
- [ ] Add dynamic visibility for task-specific components
- [ ] Add Advanced accordion with additional parameters
- [ ] Add device selection for both LLM and DiT
- [ ] Update `playground_handler.py` if needed for new parameters
- [ ] Test all task types
- [ ] Test dynamic UI visibility
- [ ] Test error handling

---

## 7. Dependencies

- gradio >= 4.0
- torch
- acestep modules (handler, llm_inference)

---

## 8. Running the Playground

```bash
# Basic
python playground/playground.py

# With options
python playground/playground.py --port 7860 --listen --share
```