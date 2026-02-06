"""
Metadata builder module for ACE-Step.

This module handles construction and parsing of metadata for music generation,
including BPM, key/scale, time signature, and other musical attributes.
"""

from typing import Dict, Any, List, Union, Optional


def create_default_meta() -> str:
    """
    Create default metadata string.
    
    Returns:
        Default metadata string in formatted style
    """
    return (
        "- bpm: N/A\n"
        "- timesignature: N/A\n"
        "- keyscale: N/A\n"
        "- duration: 30 seconds\n"
    )


def dict_to_meta_string(meta_dict: Dict[str, Any]) -> str:
    """
    Convert metadata dictionary to formatted string.
    
    Args:
        meta_dict: Dictionary containing metadata fields
        
    Returns:
        Formatted metadata string
        
    Example:
        >>> meta = {"bpm": 120, "keyscale": "C major", "timesignature": "4/4"}
        >>> dict_to_meta_string(meta)
        '- bpm: 120\\n- timesignature: 4/4\\n- keyscale: C major\\n- duration: 30 seconds\\n'
    """
    # Extract values with fallbacks
    bpm = meta_dict.get('bpm', meta_dict.get('tempo', 'N/A'))
    timesignature = meta_dict.get('timesignature', meta_dict.get('time_signature', 'N/A'))
    keyscale = meta_dict.get('keyscale', meta_dict.get('key', meta_dict.get('scale', 'N/A')))
    duration = meta_dict.get('duration', meta_dict.get('length', 30))
    
    # Format duration
    if isinstance(duration, (int, float)):
        duration = f"{int(duration)} seconds"
    elif not isinstance(duration, str):
        duration = "30 seconds"
    
    return (
        f"- bpm: {bpm}\n"
        f"- timesignature: {timesignature}\n"
        f"- keyscale: {keyscale}\n"
        f"- duration: {duration}\n"
    )


def parse_metas(metas: List[Union[str, Dict[str, Any]]]) -> List[str]:
    """
    Parse and normalize metadata inputs.
    
    Converts various metadata formats (strings, dicts) to standardized
    metadata strings with fallbacks.
    
    Args:
        metas: List of metadata in various formats (strings, dicts, or None)
        
    Returns:
        List of normalized metadata strings
    """
    parsed_metas = []
    
    for meta in metas:
        if meta is None:
            # Default fallback metadata
            parsed_meta = create_default_meta()
        elif isinstance(meta, str):
            # Already formatted string
            parsed_meta = meta
        elif isinstance(meta, dict):
            # Convert dict to formatted string
            parsed_meta = dict_to_meta_string(meta)
        else:
            # Fallback for any other type
            parsed_meta = create_default_meta()
        
        parsed_metas.append(parsed_meta)
    
    return parsed_metas


def build_metadata_dict(
    bpm: Optional[Union[int, str]],
    key_scale: str,
    time_signature: str,
    duration: Optional[float] = None
) -> Dict[str, Any]:
    """
    Build a metadata dictionary from individual components.
    
    Args:
        bpm: Beats per minute (can be int, str, or None)
        key_scale: Musical key and scale (e.g., "C major")
        time_signature: Time signature (e.g., "4/4")
        duration: Optional duration in seconds
        
    Returns:
        Dictionary containing metadata fields
    """
    metadata = {}
    
    # Handle BPM
    if bpm is not None:
        if isinstance(bpm, str):
            try:
                metadata["bpm"] = int(bpm)
            except ValueError:
                metadata["bpm"] = "N/A"
        else:
            metadata["bpm"] = bpm
    else:
        metadata["bpm"] = "N/A"
    
    # Handle key/scale
    metadata["keyscale"] = key_scale if key_scale else "N/A"
    
    # Handle time signature
    metadata["timesignature"] = time_signature if time_signature else "N/A"
    
    # Handle duration
    if duration is not None:
        metadata["duration"] = duration
    else:
        metadata["duration"] = 30
    
    return metadata


def format_instruction(instruction: str) -> str:
    """
    Format instruction to ensure it ends with a colon.
    
    Args:
        instruction: Instruction string
        
    Returns:
        Formatted instruction string
    """
    if not instruction.endswith(":"):
        instruction = instruction + ":"
    return instruction


def format_lyrics(lyrics: str, language: str) -> str:
    """
    Format lyrics with language specification.
    
    Args:
        lyrics: Lyrics text
        language: Language code or name
        
    Returns:
        Formatted lyrics string
    """
    if not lyrics:
        return ""
    
    # Add language tag if specified
    if language and language.lower() != "none":
        return f"[{language}] {lyrics}"
    
    return lyrics


def extract_caption_and_language(
    metas: List[Union[str, Dict[str, Any]]],
    captions: List[str],
    vocal_languages: List[str]
) -> tuple[List[str], List[str]]:
    """
    Extract caption and language information from metadata and inputs.
    
    This function processes metadata, captions, and language specifications
    to produce consistent caption and language lists.
    
    Args:
        metas: List of metadata (strings or dicts)
        captions: List of captions
        vocal_languages: List of language specifications
        
    Returns:
        Tuple of (processed_captions, processed_languages)
    """
    processed_captions = []
    processed_languages = []
    
    for i, meta in enumerate(metas):
        caption = captions[i] if i < len(captions) else ""
        language = vocal_languages[i] if i < len(vocal_languages) else "none"
        
        # Extract from metadata if present
        if isinstance(meta, dict):
            if "caption" in meta and not caption:
                caption = meta["caption"]
            if "language" in meta and language == "none":
                language = meta["language"]
        
        processed_captions.append(caption)
        processed_languages.append(language)
    
    return processed_captions, processed_languages
