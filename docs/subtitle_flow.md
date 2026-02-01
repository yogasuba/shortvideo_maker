# Subtitle Rendering Flow

## Overview

This document outlines the refactored subtitle rendering pipeline, designed to support both simple (English, Latin) and complex (Tamil, Hindi, Arabic) scripts with high typographical quality.

## Architecture

The system uses a **Hybrid Pipeline** to balance speed and correctness:

1.  **Simple Scripts (e.g., English, French)**:
    - **Method**: `PIL` (Python Imaging Library) overlay.
    - **Process**: Text is drawn directly onto the frame image before video generation.
    - **Pros**: Extremely fast, no external dependencies.

2.  **Complex Scripts (e.g., Tamil, Hindi, Arabic)**:
    - **Method**: `ASS` (Advanced Substation Alpha) + `libass` (via FFmpeg).
    - **Process**:
      1.  **Generate Clean Video**: Create the video scene (Image + Audio) _without_ text.
      2.  **Generate Subtitle File**: Create a `.ass` file containing the text, styles, and timing.
      3.  **Burn Subtitles**: Use FFmpeg's `ass` filter to render the subtitles onto the valid video.
    - **Pros**: Perfect text shaping (HarfBuzz), complex ligature support, professional styling (borders, shadows).
    - **Reasoning**: The previous `drawtext` filter in FFmpeg often failed to render complex scripts correctly (dotted circles, broken ligatures). `libass` is the industry standard for correct rendering.

## Detailed Flow (Complex Scripts)

### 1. Detection

The `VideoGenerator` checks the scene language. If it is in the `COMPLEX_SCRIPTS` set (e.g., `{'ta', 'hi', 'ar'}`), it triggers the ASS pipeline.

### 2. ASS File Generation (`ComplexScriptRenderer`)

- **Input**: Text, specific font path (e.g., `NotoSansTamil-Bold.ttf`), resolution.
- **Action**: Generates a file `subtitle_uuid.ass` defined with:
  - **Styles**: `Alignment=2` (Bottom Center), `FontName`, `FontSize=42`, `Outline=1`.
  - **Events**: Start/End time (matching video duration), serialized text.

### 3. Video Processing (Two-Pass)

- **Pass 1**: FFmpeg generates `raw_scene.mp4` from the input image and audio.
- **Pass 2**: FFmpeg runs:
  ```bash
  ffmpeg -i raw_scene.mp4 -vf "ass=subtitle.ass" -c:a copy output.mp4
  ```
  This "burns" the subtitles into the video frames.

## Dependencies

- **FFmpeg**: Must be compiled with `--enable-libass`.
- **Fonts**: Specific `.ttf` files (e.g., Noto Sans) must be present in `backend/fonts/`.
