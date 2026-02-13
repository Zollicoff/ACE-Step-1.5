"""
Gradio UI Components Module
Contains all Gradio interface component definitions and layouts

Layout:
  ┌──────────────────────────────────────┐
  │  Header                              │
  ├──────────────────────────────────────┤
  │  Dataset Explorer (hidden accordion) │
  ├──────────────────────────────────────┤
  │  Settings (accordion, collapsed)     │
  │   ├─ Service Configuration           │
  │   ├─ DiT Parameters                  │
  │   ├─ LM Parameters                   │
  │   └─ Output / Automation             │
  ├──────────────────────────────────────┤
  │  ┌─ Generation ─┬─ Training ──────┐  │
  │  │  Mode Radio   │  Dataset/LoRA  │  │
  │  │  Inputs       │                │  │
  │  │  Results      │                │  │
  │  └───────────────┴────────────────┘  │
  └──────────────────────────────────────┘
"""
import gradio as gr
from acestep.gradio_ui.i18n import get_i18n, t
from acestep.gradio_ui.interfaces.dataset import create_dataset_section
from acestep.gradio_ui.interfaces.generation import (
    create_advanced_settings_section,
    create_generation_tab_section,
)
from acestep.gradio_ui.interfaces.result import create_results_section
from acestep.gradio_ui.interfaces.training import create_training_section
from acestep.gradio_ui.events import setup_event_handlers, setup_training_event_handlers


def create_gradio_interface(dit_handler, llm_handler, dataset_handler, init_params=None, language='en') -> gr.Blocks:
    """
    Create Gradio interface
    
    Args:
        dit_handler: DiT handler instance
        llm_handler: LM handler instance
        dataset_handler: Dataset handler instance
        init_params: Dictionary containing initialization parameters and state.
                    If None, service will not be pre-initialized.
        language: UI language code ('en', 'zh', 'ja', default: 'en')
        
    Returns:
        Gradio Blocks instance
    """
    # Initialize i18n with selected language
    i18n = get_i18n(language)
    
    # Check if running in service mode (hide training tab)
    service_mode = init_params is not None and init_params.get('service_mode', False)
    
    with gr.Blocks(
        title=t("app.title"),
        theme=gr.themes.Soft(),
        css="""
        .main-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .section-header {
            background: linear-gradient(90deg, #4CAF50, #45a049);
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .lm-hints-row {
            align-items: stretch;
        }
        .lm-hints-col {
            display: flex;
        }
        .lm-hints-col > div {
            flex: 1;
            display: flex;
        }
        .lm-hints-btn button {
            height: 100%;
            width: 100%;
        }
        /* Position Audio time labels lower to avoid scrollbar overlap */
        .component-wrapper > .timestamps {
            transform: translateY(15px);
        }
        /* Equal-height row for instrumental checkbox + enhance lyrics button */
        .instrumental-row {
            align-items: stretch !important;
        }
        .instrumental-row > div {
            display: flex !important;
            align-items: stretch !important;
        }
        .instrumental-row > div > div {
            flex: 1;
            display: flex;
            align-items: center;
        }
        .instrumental-row button {
            height: 100% !important;
            min-height: 42px;
        }
        /* Ensure buttons in instrumental-row fill height */
        .instrumental-row > div > button {
            height: 100% !important;
            min-height: 42px;
        }
        /* Two-line icon buttons: emoji on top, text below */
        .icon-btn-wrap button, .icon-btn-wrap > button {
            word-spacing: 100vw;
            text-align: center;
            line-height: 1.4;
        }

        /* --- On-hover Tooltips --- */
        /* Hide info text by default and format as tooltip */
        span.has-info + div,
        span[data-testid="block-info"].has-info + div,
        .checkbox-container + div {
            display: none;
            position: absolute;
            background: rgba(30, 30, 30, 0.98);
            color: #ffffff;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            z-index: 10000;
            max-width: 320px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            pointer-events: none;
            line-height: 1.5;
            margin-top: 5px;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(4px);
        }

        /* Show tooltips on hover of the label area only */
        span.has-info:hover + div,
        span[data-testid="block-info"].has-info:hover + div,
        .checkbox-container:hover + div {
            display: block;
        }

        /* High-res info icon using SVG */
        span.has-info::after,
        span[data-testid="block-info"].has-info::after,
        .checkbox-container:has(+ div) .label-text::after {
            content: "";
            display: inline-block;
            width: 14px;
            height: 14px;
            margin-left: 6px;
            vertical-align: middle;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cline x1='12' y1='16' x2='12' y2='12'/%3E%3Cline x1='12' y1='8' x2='12.01' y2='8'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-size: contain;
            opacity: 0.4;
            transition: opacity 0.2s;
            cursor: help;
        }

        span.has-info:hover::after,
        span[data-testid="block-info"].has-info:hover::after,
        .checkbox-container:hover .label-text::after {
            opacity: 1;
        }
        """,
    ) as demo:
        
        gr.HTML(f"""
        <div class="main-header">
            <h1>{t("app.title")}</h1>
            <p>{t("app.subtitle")}</p>
            <p style="font-size: 0.85rem; color: #888;">{t("common.required_legend").replace("*", '<span style="color: #ff4d4d;">*</span>')}</p>
        </div>
        """)
        
        # Dataset Explorer Section (hidden)
        dataset_section = create_dataset_section(dataset_handler)
        
        # ═══════════════════════════════════════════
        # Top-level: Settings (contains Service Config + Advanced Settings)
        # ═══════════════════════════════════════════
        settings_section = create_advanced_settings_section(
            dit_handler, llm_handler, init_params=init_params, language=language
        )
        
        # ═══════════════════════════════════════════
        # Tabs: Generation | Training
        # ═══════════════════════════════════════════
        with gr.Tabs():
            # --- Generation Tab ---
            with gr.Tab(t("generation.tab_title")):
                gen_section = create_generation_tab_section(
                    dit_handler, llm_handler, init_params=init_params, language=language
                )
                
                # Results Section (inside the Generation tab, wrapped for visibility control)
                with gr.Column(visible=True) as results_wrapper:
                    results_section = create_results_section(dit_handler)
                # Store the wrapper in gen_section so event handlers can toggle it
                gen_section["results_wrapper"] = results_wrapper
            
            # --- Training Tab ---
            with gr.Tab(t("training.tab_title"), visible=not service_mode):
                training_section = create_training_section(
                    dit_handler, llm_handler, init_params=init_params
                )
        
        # ═══════════════════════════════════════════
        # Merge all generation-related component dicts for event wiring
        # ═══════════════════════════════════════════
        # The event handlers expect a single "generation_section" dict with all
        # components from settings (service config + advanced) and generation tab.
        generation_section = {}
        generation_section.update(settings_section)
        generation_section.update(gen_section)
        
        # Connect event handlers
        setup_event_handlers(
            demo, dit_handler, llm_handler, dataset_handler,
            dataset_section, generation_section, results_section
        )
        
        # Connect training event handlers
        setup_training_event_handlers(demo, dit_handler, llm_handler, training_section)
    
    return demo
