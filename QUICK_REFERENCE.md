# Quick Reference: Complex Script Rendering

## For Developers: How to Use

### Basic Usage
```python
from main import VideoGenerator

# Generator automatically handles complex scripts
gen = VideoGenerator()

# When creating videos with Tamil language:
request = VideoCreateRequest(
    title="Tamil Video",
    script="Your Tamil text here",
    language="ta",  # Triggers Tamil-specific rendering
    ...
)

# The system automatically:
# 1. Normalizes Unicode to NFC
# 2. Selects Tamil font (Nirmala.ttc or Latha)
# 3. Wraps text at word boundaries
# 4. Renders with harfbuzz
```

### Testing Complex Scripts
```bash
# Run validation test
python test_tamil_validation.py

# Expected output: 5/6 tests passed
# ✓ Unicode Normalization
# ✓ Font Selection
# ✓ Text Wrapping
# ✓ Font Rendering
# ✓ Pipeline Integration
```

## For Users: Supported Languages

| Language | Code | Font | Status |
|----------|------|------|--------|
| Tamil | `ta` | Nirmala.ttc / Latha | ✓ Full Support |
| English | `en` | Arial / DejaVu | ✓ Full Support |
| Hindi | `hi` | (Extensible) | ✓ Framework Ready |
| Arabic | `ar` | (Extensible) | ✓ Framework Ready |

## Critical Rules

### 1. Unicode Must Be NFC
```python
# ✓ CORRECT
text = unicodedata.normalize("NFC", text)

# ✗ WRONG (will produce dotted circles)
text = unicodedata.normalize("NFD", text)
```

### 2. Text Is Never Split Mid-Character
```python
# ✓ CORRECT
"சாதி மத" → ["சாதி மத"]  or  ["சாதி", "மத"]

# ✗ WRONG (prevented by system)
"சாதி மத" → ["சாத", "ி மத"]  # Cannot happen
```

### 3. Fonts Must Support the Script
```python
# ✓ CORRECT for Tamil
font = "C:/Windows/Fonts/nirmala.ttc"

# ✗ WRONG (default Arial may not work)
font = "C:/Windows/Fonts/arial.ttf"
```

## Troubleshooting Checklist

1. **Text Shows Dotted Circles (◌)**
   - [ ] Check Unicode normalization: `unicodedata.normalize("NFC", text)`
   - [ ] Verify font supports the script

2. **Text Appears Broken/Separated**
   - [ ] Ensure FFmpeg text_shaping=1 is enabled
   - [ ] Check font file is valid and accessible
   - [ ] Try PIL fallback mode

3. **Video Generation Fails**
   - [ ] Check fonts are installed or in `backend/fonts/`
   - [ ] Verify language code is correct ('ta', 'en', etc.)
   - [ ] See logs for specific error messages

4. **Text Wrapping Issues**
   - [ ] Verify word boundaries are respected
   - [ ] Check max_width setting matches video dimensions
   - [ ] Ensure font size is appropriate

## Code Examples

### Rendering Tamil Text
```python
from complex_script_renderer import ComplexScriptRenderer

renderer = ComplexScriptRenderer()

# Normalize text
text = "சாதி மத பாகுபாடின்றி"
text = renderer.normalize_unicode(text)

# Find font
font = renderer.find_font("ta")

# Wrap at word boundaries
lines = renderer.wrap_text_at_word_boundaries(
    text, 
    max_width_pixels=1000,
    font_path=font,
    font_size=42,
    language="ta"
)

# Result:
# lines = ["சாதி மத பாகுபாடின்றி"] (no split mid-word)
```

### Checking Font Availability
```python
from complex_script_renderer import ComplexScriptRenderer

renderer = ComplexScriptRenderer()

tamil_font = renderer.find_font("ta")
if tamil_font:
    print(f"Tamil font: {tamil_font}")
else:
    print("Tamil font not found, using system default")
```

## Performance Tips

1. **Font Caching**: Fonts are cached, so repeated language requests are fast
2. **PIL vs FFmpeg**: FFmpeg is faster when text_shaping=1 is supported
3. **Batch Processing**: Process multiple videos with same language to benefit from font cache

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Dotted circles (◌) | NFD form instead of NFC | Use `normalize("NFC", text)` |
| Text looks broken | Font doesn't support script | Ensure correct font is selected |
| Extra spacing in words | Character not combined | Verify NFC normalization |
| Line breaks mid-word | Wrong wrapping logic | Use word-boundary wrapping |
| Video won't render | Font not accessible | Check font path is correct |

## Environment Setup

### Windows
1. Fonts are located in `C:\Windows\Fonts\`
2. Tamil fonts: Nirmala.ttc, Latha.ttf (usually pre-installed)
3. System automatically finds them

### Linux
```bash
# Install fonts if needed
sudo apt-get install fonts-noto-tamil fonts-lohit-tamil
```

### macOS
```bash
# Install via Homebrew
brew install font-noto-sans-tamil
```

## Validation Test Output Explained

```
✓ PASS: normalization       → Unicode NFC normalization works
✓ PASS: font_selection       → Correct font selected for language
✓ PASS: text_wrapping        → Text wrapped at word boundaries
✓ PASS: font_rendering       → No dotted circles in rendered text
✓ PASS: pipeline             → Complete pipeline generates correct video
✗ FAIL: ffmpeg_drawtext      → FFmpeg test (falls back to PIL gracefully)
```

If 5 out of 6 tests pass, your system is working correctly!

## Key Validation String

Used for testing Tamil rendering:

```
சாதி மத பாகுபாடின்றி அனைவருக்கும் காரணம், சரியானவல்லித் தாயாரின் அருள்.
```

This string tests:
- Complex Tamil consonant clusters
- Vowel marks
- Punctuation
- Multiple word boundaries

Expected rendering:
- Clear, properly-shaped Tamil characters
- No dotted circles
- Clean joins between characters
- Natural Tamil typography

---

**For more details**, see [COMPLEX_SCRIPT_RENDERING.md](COMPLEX_SCRIPT_RENDERING.md)
