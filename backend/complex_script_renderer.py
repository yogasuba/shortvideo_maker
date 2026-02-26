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
from typing import Tuple, Optional, List, Dict, Any
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
        
        # Preserve explicit newlines by splitting into paragraphs first
        paragraphs = text.split('\n')
        all_wrapped_lines = []
        
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logger.warning(f"Could not load font {font_path}: {e}. Using default.")
            font = ImageFont.load_default()
        
        # Create a temporary image for measuring text
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                # Preservation of empty lines if desired, or skip
                # all_wrapped_lines.append("") 
                continue
                
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
                        all_wrapped_lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Word is so long it doesn't fit alone, must break it
                        # This is a last resort for very long words
                        logger.warning(f"Word '{word}' is too long to fit on one line. Breaking it.")
                        all_wrapped_lines.append(word)
                        current_line = []
            
            if current_line:
                all_wrapped_lines.append(' '.join(current_line))
        
        return all_wrapped_lines
    
    @staticmethod
    def generate_ass_file(
        text: str,
        output_path: Path,
        font_path: str,
        font_size: int = 60,
        duration: float = 5.0,
        resolution: str = "1080x1920",
        language: str = "en",
        margin_v: int = 100,
        style: str = "static",
        color: str = "white",
        bg_visible: bool = True,
        bold: bool = False,
        line_styles: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate ASS file with complex script support and per-line styling"""
        width, height = resolution.split('x')
        width = int(width)
        height = int(height)
        
        # Windows path handling for ASS files
        font_path = str(font_path).replace('\\', '/')
        
        # Alignment mapping
        ass_alignment = 5 if style == "center" else 2
        
        color_map = {
            'white': '&H00FFFFFF', 'yellow': '&H0000FFFF', 'cyan': '&H00FFFF00',
            'green': '&H0000FF00', 'red': '&H000000FF', 'orange': '&H0000A5FF',
            'blue': '&H00FF0000', 'pink': '&H00CBC0FF', 'purple': '&H00800080',
            'black': '&H00000000'
        }
        
        def get_ass_color(c_name, default_name='white'):
            if not c_name: return color_map.get(default_name, '&H00FFFFFF')
            return color_map.get(c_name.lower(), color_map.get(default_name, '&H00FFFFFF'))

        primary_color = get_ass_color(color)
        
        # We'll define two styles: one with Box (3) and one without (1)
        base_style_props = (
            f"{os.path.basename(font_path)},{font_size},{primary_color},"
            f"&H000000FF,&H00000000,&H60000000,"  # Sec, Out, Back
            f"{1 if bold else 0},0,0,0,100,100,0,0" # Bold... Angle
        )
        
        # Style: Box (BorderStyle 3)
        style_box = f"Style: StyleBox,{base_style_props},3,2,0,{ass_alignment},40,40,{margin_v},1"
        # Style: NoBox (BorderStyle 1)
        style_nobox = f"Style: StyleNoBox,{base_style_props},1,2,1,{ass_alignment},40,40,{margin_v},1"

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_box}
{style_nobox}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        def format_time(seconds):
            h, m, s, cs = int(seconds//3600), int((seconds%3600)//60), int(seconds%60), int((seconds*100)%100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        
        end_time = format_time(duration)
        lines = text.split('\n')
        events = []
        
        # Stacking logic (Reverse for Bottom Alignment)
        current_margin_v = margin_v
        
        # Use provided line_styles or empty list
        line_styles = line_styles or []
        
        # To stack properly from bottom up, we process lines in REVERSE order
        # for Alignment 2 (Bottom)
        for i in range(len(lines) - 1, -1, -1):
            line_text = lines[i].strip()
            if not line_text:
                current_margin_v += int(font_size * 1.2)
                continue
            
            l_style = line_styles[i] if i < len(line_styles) else {}
            
            # Determine base style name
            l_bg_visible = l_style.get('subtitle_bg_visible', bg_visible)
            style_name = "StyleBox" if l_bg_visible else "StyleNoBox"
            
            # Build override tags
            tags = []
            l_color_name = l_style.get('subtitle_color')
            if l_color_name:
                tags.append(f"\\c{get_ass_color(l_color_name)}")
                
            l_size = l_style.get('subtitle_size')
            if l_size:
                tags.append(f"\\fs{l_size}")
            else:
                l_size = font_size
                
            l_bold = l_style.get('subtitle_bold')
            if l_bold is not None:
                tags.append(f"\\b{1 if l_bold else 0}")
            
            tag_str = f"{{{(''.join(tags))}}}" if tags else ""
            events.append(f"Dialogue: 0,0:00:00.00,{end_time},{style_name},,0,0,{current_margin_v},,{tag_str}{line_text}")
            
            # Move up for next line
            current_margin_v += int(l_size * 1.3)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header)
            # Reversing events so they appear in correct order in the file (just for cleanliness)
            for ev in reversed(events):
                f.write(ev + "\n")
            
        logger.info(f"✓ Generated Per-Line ASS file: {output_path}")
        return str(output_path)
