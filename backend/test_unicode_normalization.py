#!/usr/bin/env python3
"""
Test Unicode Normalization for Tamil Text

This script tests the new normalization functions to ensure:
1. Tamil text is properly normalized using NFC (Canonical Composition)
2. Combining characters are properly handled
3. JSON parsing preserves Unicode correctly
"""

import json
import unicodedata
import sys

# Import the new functions from main
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from main import normalize_text, validate_tamil_text, safe_json_parse

def test_normalize_text():
    """Test text normalization"""
    print("=" * 60)
    print("TEST 1: Text Normalization")
    print("=" * 60)
    
    # Test cases with problematic Tamil text
    test_cases = [
        # Original text from image (with errors)
        "இந்தச் சொல்யப்பட்டும் பூணைகள் ஆன்மக் அமுதியுல் அளிக்கின்றை.",
        
        # Correct Tamil examples
        "ராமேஸ்வரம் போலவே, திலதர்ப்பணபுரி பூஜைகளுக்கும் பிரசித்தி பெற்றது.",
        
        # Mixed with English
        "This is a test: தமிழ் வாழ்க",
        
        # Simple Tamil
        "நல்ல நாள்",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Original: {text}")
        normalized = normalize_text(text, "ta")
        print(f"  Normalized: {normalized}")
        print(f"  Unicode bytes match: {text == normalized or 'DIFFERENT (Expected for some cases)'}")
        
        # Show Unicode analysis
        print(f"  Original length: {len(text)}")
        print(f"  Normalized length: {len(normalized)}")
        print(f"  Contains Tamil: {validate_tamil_text(text)}")

def test_validate_tamil():
    """Test Tamil text validation"""
    print("\n" + "=" * 60)
    print("TEST 2: Tamil Text Validation")
    print("=" * 60)
    
    test_cases = [
        ("தமிழ்", True),
        ("Tamil", False),
        ("தமிழ் Tamil", True),
        ("", False),
        ("123", False),
        ("பூனைகள்", True),
    ]
    
    for text, expected in test_cases:
        result = validate_tamil_text(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' -> {result} (expected {expected})")

def test_json_parsing():
    """Test safe JSON parsing with Unicode"""
    print("\n" + "=" * 60)
    print("TEST 3: Safe JSON Parsing")
    print("=" * 60)
    
    # Create a JSON array with Tamil text
    tamil_texts = [
        "ராமேஸ்வரம் போலவே",
        "பூஜைகளுக்கும் பிரசித்தி",
        "புனிதம் நிறைந்த திலதர்ப்பணபுரி"
    ]
    
    json_str = json.dumps(tamil_texts, ensure_ascii=False)
    print(f"\nOriginal JSON: {json_str}")
    
    # Parse using safe function
    parsed = safe_json_parse(json_str)
    print(f"\nParsed and normalized: {parsed}")
    
    # Verify all items are present and normalized
    print(f"\nVerification:")
    for i, (original, parsed_item) in enumerate(zip(tamil_texts, parsed), 1):
        # They should be equal after normalization
        normalized_original = normalize_text(original, "ta")
        match = parsed_item == normalized_original
        status = "✓" if match else "✗"
        print(f"  {status} Item {i}: {match}")

def test_nfc_decomposition():
    """Test NFC vs NFD differences"""
    print("\n" + "=" * 60)
    print("TEST 4: NFC vs NFD (Normalization Forms)")
    print("=" * 60)
    
    text = "பூனைகள்"
    nfc = unicodedata.normalize('NFC', text)
    nfd = unicodedata.normalize('NFD', text)
    
    print(f"\nOriginal: {text}")
    print(f"  Bytes: {text.encode('utf-8')}")
    print(f"  Length: {len(text)}")
    
    print(f"\nNFC (Composed): {nfc}")
    print(f"  Bytes: {nfc.encode('utf-8')}")
    print(f"  Length: {len(nfc)}")
    
    print(f"\nNFD (Decomposed): {nfd}")
    print(f"  Bytes: {nfd.encode('utf-8')}")
    print(f"  Length: {len(nfd)}")
    
    print(f"\nNFC is used for proper rendering: {nfc}")
    print(f"  This is what FFmpeg and fonts expect")

def test_character_range():
    """Test Tamil character range detection"""
    print("\n" + "=" * 60)
    print("TEST 5: Tamil Character Range")
    print("=" * 60)
    
    tamil_start = 0x0B80
    tamil_end = 0x0BFF
    
    test_text = "பூனைகள்"
    print(f"\nTamil Unicode range: U+{tamil_start:04X} to U+{tamil_end:04X}")
    print(f"\nAnalyzing: {test_text}")
    
    for char in test_text:
        code = ord(char)
        in_range = tamil_start <= code <= tamil_end
        status = "✓ Tamil" if in_range else "✗ Not Tamil"
        print(f"  {status}: '{char}' (U+{code:04X})")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Tamil Unicode Normalization Test Suite")
    print("=" * 60 + "\n")
    
    test_normalize_text()
    test_validate_tamil()
    test_json_parsing()
    test_nfc_decomposition()
    test_character_range()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60 + "\n")
