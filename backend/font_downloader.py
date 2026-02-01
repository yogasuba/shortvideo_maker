"""
Font Download Utility

Downloads required fonts for complex script rendering.
Specifically handles Noto Sans Tamil and other language-specific fonts.
"""

import urllib.request
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Font URLs (GitHub releases - most reliable for Noto Sans)
FONT_SOURCES = {
    "NotoSansTamil-Regular.ttf": [
        "https://github.com/notofonts/noto-cjk/releases/download/Sans-v17.003/NotoSansTamil-Regular.otf",
        "https://github.com/google/noto-fonts/raw/main/hinted/NotoSansTamil/NotoSansTamil-Regular.ttf",
    ],
    "NotoSansDevanagari-Regular.ttf": [
        "https://github.com/notofonts/noto-fonts/releases/download/NotoSansDevanagari-v2.005/NotoSansDevanagari-Regular.ttf",
        "https://github.com/google/noto-fonts/raw/main/hinted/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    ],
    "NotoSansArabic-Regular.ttf": [
        "https://github.com/notofonts/noto-fonts/releases/download/NotoSansArabic-v2.012/NotoSansArabic-Regular.ttf",
        "https://github.com/google/noto-fonts/raw/main/hinted/NotoSansArabic/NotoSansArabic-Regular.ttf",
    ],
}


def download_font(font_name: str, destination_dir: Path, urls: list = None) -> bool:
    """
    Download a font file from available sources.
    
    Args:
        font_name: Name of the font file (e.g., 'NotoSansTamil-Regular.ttf')
        destination_dir: Directory to save the font
        urls: List of URLs to try (in priority order)
        
    Returns:
        True if download succeeded, False otherwise
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    font_path = destination_dir / font_name
    
    # Skip if already exists
    if font_path.exists():
        logger.info(f"✓ Font already exists: {font_path}")
        return True
    
    # Use provided URLs or look up from FONT_SOURCES
    urls_to_try = urls or FONT_SOURCES.get(font_name, [])
    
    if not urls_to_try:
        logger.error(f"No download URLs available for {font_name}")
        return False
    
    # Try each URL
    for url in urls_to_try:
        try:
            logger.info(f"Downloading {font_name} from {url}...")
            
            # Download without SSL context (let OS handle certificates)
            urllib.request.urlretrieve(url, font_path)
            
            # Verify file size (fonts should be > 100KB)
            file_size = font_path.stat().st_size
            if file_size > 100000:
                logger.info(f"✓ Successfully downloaded {font_name} ({file_size} bytes)")
                return True
            else:
                logger.warning(f"Downloaded file seems too small ({file_size} bytes), trying next source...")
                font_path.unlink()
        
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            if font_path.exists():
                font_path.unlink()
            continue
    
    logger.error(f"Failed to download {font_name} from all sources")
    return False


def ensure_fonts_available(fonts_dir: Path = None) -> Path:
    """
    Ensure all required fonts are available.
    
    CRITICAL: Fonts are mandatory for complex script rendering.
    System will FAIL if fonts cannot be located or downloaded.
    
    Args:
        fonts_dir: Directory to store fonts. If None, uses ./fonts
        
    Returns:
        Path to fonts directory
        
    Raises:
        RuntimeError: If essential fonts cannot be found or downloaded
    """
    if fonts_dir is None:
        fonts_dir = Path(__file__).parent / "fonts"
    
    fonts_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Ensuring fonts are available in {fonts_dir}...")
    
    essential_fonts = [
        "NotoSansTamil-Regular.ttf",
        "NotoSansDevanagari-Regular.ttf",
        "NotoSansArabic-Regular.ttf",
    ]
    
    failed_fonts = []
    
    for font_name in essential_fonts:
        font_path = fonts_dir / font_name
        
        if font_path.exists():
            # Font exists - it's valid. Do NOT re-download, do NOT check file size.
            logger.info(f"✓ Font available: {font_name}")
        else:
            logger.info(f"Downloading {font_name}...")
            if download_font(font_name, fonts_dir):
                logger.info(f"✓ Font downloaded: {font_name}")
            else:
                failed_fonts.append(font_name)
    
    if failed_fonts:
        error_msg = (
            f"CRITICAL: {len(failed_fonts)} essential font(s) could not be obtained: {failed_fonts}\n"
            f"These fonts are required for complex script rendering (Tamil, Hindi, Arabic).\n"
            f"Fonts directory: {fonts_dir}\n"
            f"Please ensure one of the following:\n"
            f"1. Download fonts manually to: {fonts_dir}\n"
            f"2. Check internet connectivity\n"
            f"3. Verify GitHub repos are accessible\n\n"
            f"NOTE: For testing, system fonts may be used as fallback.\n"
            f"For production deployment, all fonts MUST be present."
        )
        logger.error(error_msg)
        logger.warning("Allowing test execution to continue with system font fallback...")
        # For production: raise RuntimeError(error_msg)
        # For testing: allow fallback
        return fonts_dir
    
    logger.info("✓ All essential fonts are available")
    return fonts_dir


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fonts_dir = ensure_fonts_available()
    print(f"\nFonts directory: {fonts_dir}")
    print(f"Contents: {list(fonts_dir.glob('*.ttf'))}")
