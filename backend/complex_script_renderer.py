"""
Complex Script Rendering Module

Handles proper rendering of complex scripts (Tamil, Hindi, Arabic, etc.) with:
- Unicode NFC normalization
- Proper font selection and loading
- Glyph shaping via harfbuzz/freetype
- Word-boundary-aware text wrapping
- FFmpeg drawtext with harfbuzz enabled
"""

import unicodedata
import os
import logging
from pathlib import Path
from typing import Tuple, Optional, List
import subprocess
import uuid
import textwrap

# Configure logging
logger = logging.getLogger(__name__)


class ComplexScriptRenderer:
    """Renders text in complex scripts with proper Unicode and font handling.
    
    CRITICAL CONSTRAINT:
    Complex scripts (Tamil, Hindi, Arabic, etc.) MUST NEVER render with PIL.
    Only FFmpeg drawtext with harfbuzz is acceptable for these scripts.
    
    This is because PIL cannot perform glyph shaping, resulting in:
    - Dotted circles (◌)
    - Broken ligatures
    - Incorrect character joining
    - Unreadable output
    """
    
    # Scripts that REQUIRE glyph shaping (MUST NOT use PIL)
    COMPLEX_SCRIPTS = {"ta", "hi", "te", "ml", "kn", "ar", "fa", "ur", "he"}
    
    # Supported languages and their preferred fonts
    LANGUAGE_FONT_MAP = {
        "ta": {  # Tamil
            "preferred": ["NotoSansTamil-Regular.ttf", "Lohit-Tamil.ttf", "Latha.ttf"],
            "windows_paths": [
                "C:/Windows/Fonts/NotoSansTamil-Regular.ttf",
                "C:/Windows/Fonts/Latha.ttf",
                "C:/Windows/Fonts/nirmala.ttc",
            ],
            "linux_paths": [
                "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.ttf",
                "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
            ],
            "macos_paths": [
                "/Library/Fonts/NotoSansTamil-Regular.ttf",
                "/System/Library/Fonts/Latha.ttf",
            ],
        },
        "hi": {  # Hindi
            "preferred": ["NotoSansDevanagari-Regular.ttf", "Lohit-Devanagari.ttf"],
            "windows_paths": [
                "C:/Windows/Fonts/NotoSansDevanagari-Regular.ttf",
                "C:/Windows/Fonts/mangal.ttf",
            ],
            "linux_paths": [
                "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
                "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
            ],
            "macos_paths": [
                "/Library/Fonts/NotoSansDevanagari-Regular.ttf",
            ],
        },
        "ar": {  # Arabic
            "preferred": ["NotoSansArabic-Regular.ttf", "Arial.ttf"],
            "windows_paths": [
                "C:/Windows/Fonts/NotoSansArabic-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ],
            "linux_paths": [
                "/usr/share/fonts/opentype/noto/NotoSansArabic-Regular.ttf",
            ],
            "macos_paths": [
                "/Library/Fonts/NotoSansArabic-Regular.ttf",
            ],
        },
        "en": {  # English (fallback)
            "preferred": ["Arial.ttf", "DejaVuSans.ttf"],
            "windows_paths": ["C:/Windows/Fonts/arial.ttf"],
            "linux_paths": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
            "macos_paths": ["/Library/Fonts/Arial.ttf"],
        },
    }
    
    def __init__(self, fonts_dir: Optional[Path] = None):
        """
        Initialize the renderer.
        
        Args:
            fonts_dir: Directory containing custom fonts. If provided, will search here first.
        """
        self.fonts_dir = fonts_dir
        self.font_cache = {}
    
    @staticmethod
    def assert_not_pil_for_complex_script(language: str, context: str = "") -> None:
        """
        HARD ASSERTION: Complex scripts MUST NOT render with PIL.
        
        This prevents silent failures where Tamil, Hindi, Arabic, etc.
        render with dotted circles instead of raising an error.
        
        Args:
            language: Language code (e.g., 'ta' for Tamil)
            context: Additional context for error message
            
        Raises:
            RuntimeError: If language is complex and would fallback to PIL
        """
        if language in ComplexScriptRenderer.COMPLEX_SCRIPTS:
            error_msg = (
                f"CRITICAL ERROR: Attempted to render {language.upper()} text with PIL!\n"
                f"PIL cannot shape complex scripts. This results in:\n"
                f"  • Dotted circles (◌) instead of proper glyphs\n"
                f"  • Broken ligatures and character joins\n"
                f"  • Unreadable output\n"
                f"\n"
                f"SOLUTION:\n"
                f"  1. Ensure FFmpeg is compiled with --enable-libharfbuzz\n"
                f"  2. Download fonts from: backend/fonts/\n"
                f"  3. Use FFmpeg drawtext rendering ONLY\n"
                f"\n"
                f"Context: {context}"
            )
            raise RuntimeError(error_msg)
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Normalize text to NFC form immediately after extraction.
        
        This is CRITICAL for complex scripts. NFC ensures:
        - Composed characters are used instead of decomposed
        - Proper glyph shaping
        - No dotted circles (◌) appearing
        - Correct rendering by font engines
        
        Args:
            text: Input text (may be in NFD or other forms)
            
        Returns:
            Text normalized to NFC form
        """
        if not text:
            return ""
        
        # Normalize to NFC (composed form)
        normalized = unicodedata.normalize("NFC", text)
        
        # Log if normalization made changes (helps debug)
        if normalized != text:
            logger.debug(f"Unicode normalization changed text: {text!r} → {normalized!r}")
        
        return normalized
    
    def find_font(self, language: str = "en") -> Optional[str]:
        """
        Find the best available font for the specified language.
        
        Priority order:
        1. Custom fonts in fonts_dir
        2. Noto Sans fonts (preferred, comprehensive Unicode support)
        3. System language-specific fonts (Latha, Lohit, etc.)
        4. Fallback to Arial/DejaVu
        
        Args:
            language: Language code (e.g., 'ta' for Tamil, 'en' for English)
            
        Returns:
            Path to the font file, or None if not found
        """
        if language in self.font_cache:
            return self.font_cache[language]
        
        lang_fonts = self.LANGUAGE_FONT_MAP.get(language, self.LANGUAGE_FONT_MAP["en"])
        
        # 1. Check custom fonts directory first (HIGHEST PRIORITY)
        if self.fonts_dir and self.fonts_dir.exists():
            for font_name in lang_fonts.get("preferred", []):
                font_path = self.fonts_dir / font_name
                if font_path.exists():
                    logger.info(f"✓ Found custom font for {language}: {font_path}")
                    self.font_cache[language] = str(font_path)
                    return str(font_path)
            
            # For complex scripts, NEVER fall back to system fonts if custom font dir exists
            if language in self.COMPLEX_SCRIPTS:
                error_msg = (
                    f"CRITICAL: No custom font found for complex script '{language}' in {self.fonts_dir}\n"
                    f"Custom fonts are MANDATORY for complex script rendering.\n"
                    f"Expected font: {lang_fonts.get('preferred', ['unknown'])[0]}\n"
                    f"Please ensure font is downloaded to: {self.fonts_dir}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        # 2. For simple scripts only: Check OS-specific system fonts
        if os.name == 'nt':  # Windows
            paths_to_check = lang_fonts.get("windows_paths", [])
        elif os.uname().sysname == 'Darwin':  # macOS
            paths_to_check = lang_fonts.get("macos_paths", [])
        else:  # Linux
            paths_to_check = lang_fonts.get("linux_paths", [])
        
        for font_path in paths_to_check:
            if os.path.exists(font_path):
                logger.info(f"✓ Found system font for {language}: {font_path}")
                self.font_cache[language] = font_path
                return font_path
        
        # 3. For simple scripts, fallback to English if language not found
        if language != "en":
            logger.warning(f"No font found for {language}, falling back to English")
            return self.find_font("en")
        
        logger.error(f"No font found for English! This is a critical issue.")
        return None
    
    @staticmethod
    def wrap_text_at_word_boundaries(
        text: str, 
        max_width_pixels: int, 
        font_path: str,
        font_size: int,
        language: str = "en"
    ) -> List[str]:
        """
        Wrap text at word boundaries ONLY, never in the middle of words.
        
        This prevents Tamil/complex script characters from being split.
        
        Args:
            text: The text to wrap (MUST be NFC normalized)
            max_width_pixels: Maximum width in pixels per line
            font_path: Path to the font file
            font_size: Font size in pixels
            language: Language code for proper word detection
            
        Returns:
            List of text lines that fit within max_width_pixels
        """
        from PIL import ImageFont, Image, ImageDraw
        
        lines = []
        
        # For complex scripts, simple space-splitting may not work perfectly
        # but it's better than splitting in the middle of ligatures
        words = text.split()
        
        if not words:
            return []
        
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logger.warning(f"Could not load font {font_path}: {e}. Using default.")
            font = ImageFont.load_default()
        
        # Create a temporary image for measuring text
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)
        
        current_line = []
        
        for word in words:
            # Test if adding this word would exceed the width
            test_line = ' '.join(current_line + [word])
            
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except Exception as e:
                logger.warning(f"Could not measure text: {e}")
                line_width = 0
            
            if line_width <= max_width_pixels:
                # Word fits on current line
                current_line.append(word)
            else:
                # Word doesn't fit
                if current_line:
                    # Save current line and start a new one
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is so long it doesn't fit alone, must break it
                    # This is a last resort for very long words
                    logger.warning(f"Word '{word}' is too long to fit on one line. Breaking it (not ideal for complex scripts).")
                    # For complex scripts, we try to at least keep it as one chunk
                    # rather than breaking in the middle
                    lines.append(word)
        
        # Don't forget the last line
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    @staticmethod
    def generate_ass_file(
        text: str,
        output_path: Path,
        font_path: str,
        font_size: int = 42,
        duration: float = 5.0,
        resolution: str = "1080x1920",
        language: str = "en"
    ) -> str:
        """
        Generate an ASS (Advanced Substation Alpha) subtitle file.
        
        This is the INDUSTRY STANDARD for rendering complex scripts (Tamil, Hindi, etc.)
        because it allows libass + HarfBuzz to handle text shaping correctly.
        
        Args:
            text: Normalized text to display
            output_path: Path to save the .ass file
            font_path: Path to the font file
            font_size: Font size
            duration: Duration of the subtitle
            resolution: Video resolution "WxH"
            language: Language code
            
        Returns:
            Path to the generated .ass file
        """
        width, height = resolution.split('x')
        width = int(width)
        height = int(height)
        
        # Windows path handling for ASS files (forward slashes are safer for libass)
        font_path = str(font_path).replace('\\', '/')
        
        # Create valid ASS header
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{os.path.basename(font_path)},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Calculate duration in H:MM:SS.cs format
        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds * 100) % 100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        
        end_time = format_time(duration)
        
        # Prepare text: Replace newlines with \N for ASS
        # NOTE: We DO NOT double escape like for FFmpeg command line
        ass_text = text.replace('\n', r'\N')
        
        event_line = f"Dialogue: 0,0:00:00.00,{end_time},Default,,0,0,0,,{ass_text}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write(event_line)
            
        logger.info(f"✓ Generated ASS file: {output_path}")
        return str(output_path)
