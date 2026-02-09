import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from complex_script_renderer import ComplexScriptRenderer

def test_scroll_ass():
    renderer = ComplexScriptRenderer()
    font_path = "C:/Windows/Fonts/arial.ttf"
    output_path = Path("test_scroll.ass")
    text = "This is a scrolling text\nfor movie credits style."
    
    # Generate scrolling ASS
    renderer.generate_ass_file(
        text=text,
        output_path=output_path,
        font_path=font_path,
        duration=5.0,
        style="scroll_up"
    )
    
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("Generated ASS Content:")
            print(content)
            
            if "\\move(" in content:
                print("\nSUCCESS: Found \\move tag in ASS file!")
            else:
                print("\nFAILURE: \\move tag NOT found in ASS file.")
        
        # Cleanup
        # output_path.unlink()
    else:
        print("FAILURE: ASS file not created.")

if __name__ == "__main__":
    test_scroll_ass()
