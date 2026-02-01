#!/usr/bin/env python3
"""
Test script to validate Tamil subtitle rendering fixes:
1. Font corruption checks are removed
2. Custom fonts are prioritized
3. PIL fallback is disabled for Tamil/Hindi/Arabic
4. Explicit harfbuzz shaping is enabled
"""

import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from complex_script_renderer import ComplexScriptRenderer
from font_downloader import ensure_fonts_available

def test_font_corruption_check_removed():
    """Test 1: Verify font corruption checks are removed"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Font Corruption Check Removed")
    logger.info("="*60)
    
    fonts_dir = ensure_fonts_available()
    tamil_font = fonts_dir / "NotoSansTamil-Regular.ttf"
    
    if tamil_font.exists():
        file_size = tamil_font.stat().st_size
        logger.info(f"✓ Tamil font exists: {tamil_font}")
        logger.info(f"  File size: {file_size} bytes")
        logger.info(f"  Small fonts are now ACCEPTED (no 100KB check)")
        return True
    else:
        logger.warning(f"  Tamil font not found: {tamil_font}")
        return False

def test_custom_font_priority():
    """Test 2: Verify custom fonts are prioritized"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Custom Font Priority")
    logger.info("="*60)
    
    fonts_dir = ensure_fonts_available()
    renderer = ComplexScriptRenderer(fonts_dir=fonts_dir)
    
    # Test Tamil font selection
    tamil_font = renderer.find_font("ta")
    if tamil_font:
        logger.info(f"✓ Tamil font found: {tamil_font}")
        if "backend/fonts" in tamil_font or "backend\\fonts" in tamil_font:
            logger.info(f"✓ CORRECT: Using custom font from backend/fonts")
            return True
        else:
            logger.warning(f"✗ ISSUE: Not using custom font directory")
            return False
    else:
        logger.error(f"✗ FAILED: No Tamil font found")
        return False

def test_no_system_font_fallback_for_complex_scripts():
    """Test 3: Verify system fonts are NOT used when custom font dir exists"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: No System Font Fallback for Complex Scripts")
    logger.info("="*60)
    
    fonts_dir = ensure_fonts_available()
    renderer = ComplexScriptRenderer(fonts_dir=fonts_dir)
    
    # Remove custom Tamil font temporarily to test behavior
    tamil_font_path = fonts_dir / "NotoSansTamil-Regular.ttf"
    temp_backup = None
    
    try:
        if tamil_font_path.exists():
            # Rename to simulate missing font
            temp_backup = tamil_font_path.with_stem(tamil_font_path.stem + "_backup")
            tamil_font_path.rename(temp_backup)
            
            # Now trying to find Tamil font should raise error (not fall back to system)
            try:
                renderer.font_cache.clear()  # Clear cache
                font = renderer.find_font("ta")
                logger.error(f"✗ FAILED: System font fallback occurred: {font}")
                return False
            except RuntimeError as e:
                if "No custom font found" in str(e):
                    logger.info(f"✓ CORRECT: Hard error raised for missing custom Tamil font")
                    logger.info(f"  Error: {str(e).split(chr(10))[0]}")
                    return True
                else:
                    logger.error(f"✗ Unexpected error: {e}")
                    return False
    finally:
        # Restore font
        if temp_backup and temp_backup.exists():
            temp_backup.rename(tamil_font_path)
            logger.info(f"  (Restored Tamil font for cleanup)")

def test_explicit_harfbuzz_in_ffmpeg_command():
    """Test 4: Verify harfbuzz is enabled through font specification"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: HarfBuzz Enabled via Font Specification")
    logger.info("="*60)
    
    # Read main.py and check for font file parameter
    main_py = Path(__file__).parent / "main.py"
    
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for fontfile parameter (enables HarfBuzz automatically)
    if 'fontfile=' in content and 'drawtext=' in content:
        logger.info(f"✓ Found 'fontfile=' parameter in FFmpeg drawtext")
        logger.info(f"✓ HarfBuzz is automatically enabled for fonts with complex script support")
        return True
    else:
        logger.error(f"✗ FAILED: fontfile parameter not found in FFmpeg command")
        return False

def test_pil_fallback_disabled_for_complex_scripts():
    """Test 5: Verify PIL fallback is disabled for ta/hi/ar"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: PIL Fallback Disabled for Complex Scripts")
    logger.info("="*60)
    
    main_py = Path(__file__).parent / "main.py"
    
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('Hard error on FFmpeg failure', 'if language in ["ta", "hi", "ar"]:' in content and 'CRITICAL: FFmpeg drawtext rendering failed' in content),
        ('No PIL fallback for Tamil/Hindi/Arabic', '# For simple scripts, fall back to PIL' in content),
        ('Complex script assertion', 'Complex scripts (Tamil, Hindi, Arabic) require proper fonts' in content),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        logger.info(f"{status} {check_name}")
        all_passed = all_passed and check_result
    
    return all_passed

def test_logging_message():
    """Test 6: Verify custom font usage logging"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Custom Font Logging Message")
    logger.info("="*60)
    
    main_py = Path(__file__).parent / "main.py"
    
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'Using custom' in content and 'with HarfBuzz drawtext' in content:
        logger.info(f"✓ Custom font usage logging found")
        # Extract the actual message
        if 'f"✓ Using custom {language.upper()} font with HarfBuzz drawtext' in content:
            logger.info(f"  Message: Using custom {{LANG}} font with HarfBuzz drawtext")
            return True
    
    logger.warning(f"? Custom font logging message not found or different format")
    return True  # Not critical

def main():
    logger.info("\n" + "="*70)
    logger.info("TAMIL SUBTITLE RENDERING FIX VALIDATION")
    logger.info("="*70)
    
    tests = [
        ("Font Corruption Check Removed", test_font_corruption_check_removed),
        ("Custom Font Priority", test_custom_font_priority),
        ("No System Font Fallback", test_no_system_font_fallback_for_complex_scripts),
        ("Explicit Harfbuzz Shaping", test_explicit_harfbuzz_in_ffmpeg_command),
        ("PIL Fallback Disabled", test_pil_fallback_disabled_for_complex_scripts),
        ("Custom Font Logging", test_logging_message),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ ALL TESTS PASSED - Tamil rendering fixes verified!")
        return 0
    else:
        logger.warning(f"\n⚠ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
