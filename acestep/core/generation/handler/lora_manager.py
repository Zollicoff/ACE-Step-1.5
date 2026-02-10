"""LoRA management mixin for AceStepHandler."""

import os
from typing import Any, Dict

from loguru import logger


class LoraManagerMixin:
    def load_lora(self, lora_path: str) -> str:
        """Load LoRA adapter into the decoder."""
        if self.model is None:
            return "❌ Model not initialized. Please initialize service first."

        # Check if model is quantized - LoRA loading on quantized models is not supported
        # due to incompatibility between PEFT and torchao (missing get_apply_tensor_subclass argument)
        if self.quantization is not None:
            return (
                f"❌ LoRA loading is not supported on quantized models. "
                f"Current quantization: {self.quantization}. "
                "Please re-initialize the service with quantization disabled, then try loading the LoRA adapter again."
            )

        if not lora_path or not lora_path.strip():
            return "❌ Please provide a LoRA path."

        lora_path = lora_path.strip()

        # Check if path exists
        if not os.path.exists(lora_path):
            return f"❌ LoRA path not found: {lora_path}"

        # Check if it's a valid PEFT adapter directory
        config_file = os.path.join(lora_path, "adapter_config.json")
        if not os.path.exists(config_file):
            return f"❌ Invalid LoRA adapter: adapter_config.json not found in {lora_path}"

        try:
            from peft import PeftModel, PeftConfig
        except ImportError:
            return "❌ PEFT library not installed. Please install with: pip install peft"

        try:
            import copy
            # Backup base decoder if not already backed up
            if self._base_decoder is None:
                self._base_decoder = copy.deepcopy(self.model.decoder)
                logger.info("Base decoder backed up")
            else:
                # Restore base decoder before loading new LoRA
                self.model.decoder = copy.deepcopy(self._base_decoder)
                logger.info("Restored base decoder before loading new LoRA")

            # Load PEFT adapter
            logger.info(f"Loading LoRA adapter from {lora_path}")
            self.model.decoder = PeftModel.from_pretrained(
                self.model.decoder,
                lora_path,
                is_trainable=False,
            )
            self.model.decoder = self.model.decoder.to(self.device).to(self.dtype)
            self.model.decoder.eval()

            self.lora_loaded = True
            self.use_lora = True  # Enable LoRA by default after loading

            logger.info(f"LoRA adapter loaded successfully from {lora_path}")
            return f"✅ LoRA loaded from {lora_path}"

        except Exception as e:
            logger.exception("Failed to load LoRA adapter")
            return f"❌ Failed to load LoRA: {str(e)}"

    def unload_lora(self) -> str:
        """Unload LoRA adapter and restore base decoder."""
        if not self.lora_loaded:
            return "⚠️ No LoRA adapter loaded."

        if self._base_decoder is None:
            return "❌ Base decoder backup not found. Cannot restore."

        try:
            import copy
            # Restore base decoder
            self.model.decoder = copy.deepcopy(self._base_decoder)
            self.model.decoder = self.model.decoder.to(self.device).to(self.dtype)
            self.model.decoder.eval()

            self.lora_loaded = False
            self.use_lora = False
            self.lora_scale = 1.0  # Reset scale to default

            logger.info("LoRA unloaded, base decoder restored")
            return "✅ LoRA unloaded, using base model"

        except Exception as e:
            logger.exception("Failed to unload LoRA")
            return f"❌ Failed to unload LoRA: {str(e)}"

    def set_use_lora(self, use_lora: bool) -> str:
        """Toggle LoRA usage for inference."""
        if use_lora and not self.lora_loaded:
            return "❌ No LoRA adapter loaded. Please load a LoRA first."

        self.use_lora = use_lora

        # Use PEFT's enable/disable methods if available
        if self.lora_loaded and hasattr(self.model.decoder, "disable_adapter_layers"):
            try:
                if use_lora:
                    self.model.decoder.enable_adapter_layers()
                    logger.info("LoRA adapter enabled")
                    # Apply current scale when enabling LoRA
                    if self.lora_scale != 1.0:
                        self.set_lora_scale(self.lora_scale)
                else:
                    self.model.decoder.disable_adapter_layers()
                    logger.info("LoRA adapter disabled")
            except Exception as e:
                logger.warning(f"Could not toggle adapter layers: {e}")

        status = "enabled" if use_lora else "disabled"
        return f"✅ LoRA {status}"

    def set_lora_scale(self, scale: float) -> str:
        """Set LoRA adapter scale/weight (0-1 range)."""
        if not self.lora_loaded:
            return "⚠️ No LoRA loaded"

        # Clamp scale to 0-1 range
        self.lora_scale = max(0.0, min(1.0, scale))

        # Only apply scaling if LoRA is enabled
        if not self.use_lora:
            logger.info(f"LoRA scale set to {self.lora_scale:.2f} (will apply when LoRA is enabled)")
            return f"✅ LoRA scale: {self.lora_scale:.2f} (LoRA disabled)"

        # Iterate through LoRA layers only and set their scaling.
        # Keep the legacy path first for backward compatibility.
        try:
            modified_count = 0
            for name, module in self.model.decoder.named_modules():
                # Only modify LoRA modules - they have 'lora_' in their name
                # This prevents modifying attention scaling and other non-LoRA modules
                if "lora_" in name and hasattr(module, "scaling"):
                    scaling = module.scaling
                    # Handle dict-style scaling (adapter_name -> value)
                    if isinstance(scaling, dict):
                        # Save original scaling on first call
                        if not hasattr(module, "_original_scaling"):
                            module._original_scaling = {k: v for k, v in scaling.items()}
                        # Apply new scale
                        for adapter_name in scaling:
                            module.scaling[adapter_name] = module._original_scaling[adapter_name] * self.lora_scale
                        modified_count += 1
                    # Handle float-style scaling (single value)
                    elif isinstance(scaling, (int, float)):
                        if not hasattr(module, "_original_scaling"):
                            module._original_scaling = scaling
                        module.scaling = module._original_scaling * self.lora_scale
                        modified_count += 1

            # Fallback for PEFT runtimes that expose LoRA scaling via methods
            # (e.g. peft.tuners.lora.layer.LoraLayer.set_scale / scale_layer)
            if modified_count == 0:
                active_adapters = []
                if hasattr(self.model.decoder, "active_adapters"):
                    adapters = self.model.decoder.active_adapters
                    if callable(adapters):
                        adapters = adapters()
                    if isinstance(adapters, str):
                        active_adapters = [adapters]
                    elif isinstance(adapters, (list, tuple, set)):
                        active_adapters = [a for a in adapters if isinstance(a, str)]
                if not active_adapters and hasattr(self.model.decoder, "peft_config"):
                    config = getattr(self.model.decoder, "peft_config", {})
                    if isinstance(config, dict):
                        active_adapters = [k for k in config.keys() if isinstance(k, str)]

                for _, module in self.model.decoder.named_modules():
                    module_name = module.__class__.__module__.lower()
                    class_name = module.__class__.__name__.lower()
                    is_probably_lora_layer = (
                        "peft" in module_name and "lora" in module_name
                    ) or ("lora" in class_name)
                    if not is_probably_lora_layer:
                        continue

                    module_modified = False
                    if hasattr(module, "set_scale") and active_adapters:
                        for adapter_name in active_adapters:
                            try:
                                module.set_scale(adapter_name, self.lora_scale)
                                module_modified = True
                            except Exception:
                                continue
                    elif hasattr(module, "scale_layer"):
                        try:
                            module.scale_layer(self.lora_scale)
                            module_modified = True
                        except Exception:
                            pass

                    if module_modified:
                        modified_count += 1

            if modified_count > 0:
                logger.info(f"LoRA scale set to {self.lora_scale:.2f} (modified {modified_count} modules)")
                return f"✅ LoRA scale: {self.lora_scale:.2f}"
            else:
                logger.warning("No LoRA scaling attributes found to modify")
                return f"⚠️ Scale set to {self.lora_scale:.2f} (no modules found)"
        except Exception as e:
            logger.warning(f"Could not set LoRA scale: {e}")
            return f"⚠️ Scale set to {self.lora_scale:.2f} (partial)"

    def get_lora_status(self) -> Dict[str, Any]:
        """Get current LoRA status."""
        return {
            "loaded": self.lora_loaded,
            "active": self.use_lora,
            "scale": self.lora_scale,
        }
