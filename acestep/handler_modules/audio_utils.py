"""
Audio utility functions for ACE-Step.

This module contains utility functions for audio processing including:
- Audio silence detection
- Audio normalization
- Stereo conversion and resampling
"""

import torch
import torchaudio


def is_silence(audio: torch.Tensor, threshold: float = 1e-4) -> bool:
    """
    Check if audio is effectively silent.
    
    Args:
        audio: Audio tensor to check
        threshold: Amplitude threshold below which audio is considered silent
        
    Returns:
        True if audio is silent, False otherwise
    """
    return audio.abs().max() < threshold


def normalize_audio_to_stereo_48k(
    audio: torch.Tensor, 
    sr: int, 
    target_sr: int = 48000
) -> torch.Tensor:
    """
    Normalize audio to stereo format at 48kHz sample rate.
    
    Handles mono/stereo conversion and resampling.
    
    Args:
        audio: Input audio tensor [channels, samples]
        sr: Source sample rate
        target_sr: Target sample rate (default: 48000)
        
    Returns:
        Normalized stereo audio at target sample rate [2, samples]
    """
    # Resample if needed
    if sr != target_sr:
        audio = torchaudio.functional.resample(audio, sr, target_sr)
    
    # Convert to stereo
    if audio.shape[0] == 1:
        # Mono to stereo: duplicate channel
        audio = audio.repeat(2, 1)
    elif audio.shape[0] > 2:
        # Multi-channel to stereo: take first 2 channels
        audio = audio[:2]
    
    return audio


def normalize_audio_code_hints(
    audio_code_hints: torch.Tensor | list[str] | str | None,
    batch_size: int
) -> list[str | None]:
    """
    Normalize audio code hints to a list of strings or None values.
    
    Args:
        audio_code_hints: Audio code hints in various formats
        batch_size: Target batch size
        
    Returns:
        List of audio code hint strings or None values, length = batch_size
    """
    if audio_code_hints is None:
        return [None] * batch_size
    
    if isinstance(audio_code_hints, str):
        # Single string -> replicate for batch
        return [audio_code_hints] * batch_size
    
    if isinstance(audio_code_hints, list):
        if len(audio_code_hints) == 0:
            return [None] * batch_size
        
        if len(audio_code_hints) == 1:
            # Single item list -> replicate
            return audio_code_hints * batch_size
        
        if len(audio_code_hints) != batch_size:
            raise ValueError(
                f"audio_code_hints length ({len(audio_code_hints)}) "
                f"must be 1 or match batch_size ({batch_size})"
            )
        
        return audio_code_hints
    
    raise TypeError(
        f"audio_code_hints must be str, list, or None, got {type(audio_code_hints)}"
    )


def normalize_instructions(
    instructions: str | list[str] | None,
    batch_size: int,
    default: str | None = None
) -> list[str]:
    """
    Normalize instructions to a list of strings.
    
    Args:
        instructions: Instructions in various formats
        batch_size: Target batch size
        default: Default instruction if instructions is None
        
    Returns:
        List of instruction strings, length = batch_size
    """
    if instructions is None:
        if default is None:
            raise ValueError("instructions and default cannot both be None")
        return [default] * batch_size
    
    if isinstance(instructions, str):
        # Single string -> replicate for batch
        return [instructions] * batch_size
    
    if isinstance(instructions, list):
        if len(instructions) == 0:
            if default is None:
                raise ValueError("Empty instructions list and no default provided")
            return [default] * batch_size
        
        if len(instructions) == 1:
            # Single item list -> replicate
            return instructions * batch_size
        
        if len(instructions) != batch_size:
            raise ValueError(
                f"instructions length ({len(instructions)}) "
                f"must be 1 or match batch_size ({batch_size})"
            )
        
        return instructions
    
    raise TypeError(
        f"instructions must be str, list, or None, got {type(instructions)}"
    )


def pad_sequences(
    sequences: list[torch.Tensor], 
    max_length: int, 
    pad_value: int = 0
) -> torch.Tensor:
    """
    Pad a list of sequences to the same length.
    
    Args:
        sequences: List of 1D tensors to pad
        max_length: Target length for all sequences
        pad_value: Value to use for padding
        
    Returns:
        Padded tensor of shape [len(sequences), max_length]
    """
    padded = torch.full(
        (len(sequences), max_length),
        pad_value,
        dtype=sequences[0].dtype,
        device=sequences[0].device
    )
    
    for i, seq in enumerate(sequences):
        length = min(seq.shape[0], max_length)
        padded[i, :length] = seq[:length]
    
    return padded
