import PIL
from PIL import Image, ImageDraw, ImageFont
import os

print(f"Pillow Version: {PIL.__version__}")

try:
    from PIL import features
    print(f"Raqm Available: {features.check('raqm')}")
except Exception as e:
    print(f"Features check failed: {e}")

# Test Tamil Rendering
text = "இறைவன் முக்தீஸ்வரர்"
font_path = "C:/Windows/Fonts/Nirmala.ttc"

if os.path.exists(font_path):
    img = Image.new('RGB', (500, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, 32)
        draw.text((10, 10), text, font=font, fill=(0, 0, 0))
        img.save("tamil_test_normal.png")
        print("Saved tamil_test_normal.png")
        
        # Try with direction/language if Raqm
        if features.check('raqm'):
            img_raqm = Image.new('RGB', (500, 100), color=(255, 255, 255))
            draw_raqm = ImageDraw.Draw(img_raqm)
            draw_raqm.text((10, 10), text, font=font, fill=(0, 0, 0), direction='ltr', language='ta')
            img_raqm.save("tamil_test_raqm.png")
            print("Saved tamil_test_raqm.png")
    except Exception as e:
        print(f"Rendering failed: {e}")
else:
    print("Nirmala.ttc not found")
