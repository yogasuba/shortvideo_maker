#!/usr/bin/env python3
"""
Test Tamil subtitles end-to-end
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from subtitle_processor import clean_text_for_language, validate_text_for_language

# Test with actual Tamil text
test_tamil_scenes = [
    {
        "scene_number": 1,
        "text": "வணக்கம் நண்பர்களே"
    },
    {
        "scene_number": 2,
        "text": "இந்தியாவின் புகழ் பெற்ற பिதा"
    },
    {
        "scene_number": 3,
        "text": "ரிசர்ச் செய்யும் மாணவர்கள்"
    }
]

print("=" * 70)
print("TAMIL SUBTITLE END-TO-END TEST")
print("=" * 70)

# Simulate what the backend does
language = "ta"  # Tamil

for scene in test_tamil_scenes:
    print(f"\nScene {scene['scene_number']}:")
    print(f"  Original text: '{scene['text']}'")
    
    # This is what main.py does
    subtitle_text = scene.get('voice_over', scene.get('text', ''))
    
    if not subtitle_text or not subtitle_text.strip():
        print(f"  ⚠️  WARNING: Empty subtitle text! This will render as empty box!")
        continue
    
    # Clean the text
    cleaned_text, report = clean_text_for_language(subtitle_text, language)
    
    print(f"  Cleaned text: '{cleaned_text}'")
    print(f"  Text length: {len(cleaned_text)} chars")
    
    if report['corrections_applied']:
        print(f"  Corrections: {', '.join(report['corrections_applied'])}")
    
    # Validate
    is_valid, issues = validate_text_for_language(cleaned_text, language)
    print(f"  Valid: {is_valid}")
    if issues:
        print(f"  Issues: {', '.join(issues)}")
    
    # What will be rendered
    print(f"  ✓ Will render: '{cleaned_text}'")

print("\n" + "=" * 70)
print("TROUBLESHOOTING:")
print("=" * 70)
print("If you see 'Empty subtitle text!' above, it means:")
print("1. Your scenes don't have 'text' field populated")
print("2. The 'voice_over' field is empty")
print("3. The script wasn't processed correctly")
print("\nSOLUTION:")
print("- Make sure you provide Tamil text in your script or scenes")
print("- The language should be set to 'ta' (Tamil)")
print("- Use Tamil script (Unicode range U+0B80-U+0BFF)")
print("=" * 70)
