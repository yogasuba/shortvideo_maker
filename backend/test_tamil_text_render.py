#!/usr/bin/env python3
"""
Test to debug why Tamil text might be empty in rendered subtitles
"""
import json
from pathlib import Path
from subtitle_processor import clean_text_for_language, generate_processing_report

# Sample Tamil texts that should be rendered
test_texts = {
    "tamil_hello": "வணக்கம்",
    "tamil_thank_you": "நன்றி", 
    "tamil_sentence": "இந்தியாவின் புக்கிய பிதா",
    "tamil_complex": "ரிசர்ச் செய்யும் மாணவர்கள்"
}

print("=" * 60)
print("TAMIL TEXT RENDERING DEBUG TEST")
print("=" * 60)

# Test 1: Check subtitle config
print("\n1. CHECKING SUBTITLE CONFIG")
config_path = Path(__file__).parent / "subtitle_config.json"
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    tamil_config = config['subtitle_styling']['tamil']
    print(f"   ✓ Config loaded successfully")
    print(f"   Font: {tamil_config['font_name']}")
    print(f"   Background Alpha: {tamil_config['background_alpha']}")
    print(f"   Padding H: {tamil_config['padding_horizontal']}, V: {tamil_config['padding_vertical']}")
except Exception as e:
    print(f"   ✗ Error loading config: {e}")

# Test 2: Check text cleaning function
print("\n2. TESTING TEXT CLEANING")
for name, tamil_text in test_texts.items():
    print(f"\n   Testing: {name}")
    print(f"   Input:  '{tamil_text}'")
    cleaned_text, report = clean_text_for_language(tamil_text, 'tamil')
    print(f"   Output: '{cleaned_text}'")
    print(f"   Output Length: {len(cleaned_text)} chars")
    
    if not cleaned_text or cleaned_text.strip() == '':
        print(f"   ⚠️  WARNING: Text became empty after cleaning!")
    else:
        print(f"   ✓ Text preserved")
    
    if report['corrections_applied']:
        print(f"   Corrections: {report['corrections_applied']}")
    if report['issues_found']:
        print(f"   Issues: {report['issues_found']}")

# Test 3: Check what happens with empty input
print("\n3. TESTING EMPTY/NULL INPUT")
for empty_val in ["", None, "   ", "\n"]:
    result, _ = clean_text_for_language(empty_val if empty_val is not None else "", 'tamil')
    print(f"   Input '{repr(empty_val)}' → Output '{repr(result)}'")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
