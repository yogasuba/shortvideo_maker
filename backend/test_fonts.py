from PIL import Image, ImageDraw, ImageFont
import os

tamil_text = "சாதி மக பட்டுமி இன்றி அனைவரக்கும் கார்ணய தர்ப்பணம் வழங்கப்படும் இதயுதகே நாட"

fonts = [
    ("C:/Windows/Fonts/Nirmala.ttc", 1),  # index 1 for TTC
    ("C:/Windows/Fonts/Nirmala.ttf", 0),
]

print("Testing Tamil fonts:")
for font_path, index in fonts:
    if os.path.exists(font_path):
        try:
            if font_path.endswith('.ttc'):
                font = ImageFont.truetype(font_path, 48, index=index)
            else:
                font = ImageFont.truetype(font_path, 48)
            print(f"✓ {os.path.basename(font_path)} loads successfully at index {index}")
        except Exception as e:
            print(f"✗ {os.path.basename(font_path)} failed: {e}")
    else:
        print(f"✗ {os.path.basename(font_path)} not found")
