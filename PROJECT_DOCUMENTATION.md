# Project Documentation

## 1. Project Overview

The **Faceless Videos Creator** is an automated tool that generates short-form videos from user-provided text scripts. It uses AI to split scripts into scenes, generate voiceovers (TTS), fetch or generate visual assets (images/videos), and stitch everything together using FFmpeg.

## 2. File Structure & Storage

- **backend/**: Contains the FastAPI server and logic.
  - `main.py`: The core application code.
  - `storage/`: **CRITICAL**. This is where all generated and uploaded assets are stored.
    - `storage/visuals/`: Stores AI-generated images and **User Uploaded Images**.
    - `storage/audio/`: Stores generated TTS audio files.
    - `storage/scenes/`: Stores individual video segments (one per scene).
    - `storage/videos/`: Stores the final concatenated videos.
    - `storage/temp/`: Temporary files (subtitles, resizing).
  - `voices.json`: Configuration definitions.
- **frontend/**: Contains the client-side code.
  - `index.html`: The single-page application (UI).

## 3. Backend Details (`backend/main.py`)

### Classes & Logic

#### `Config`

Static configuration class.

- **`STORAGE_DIR`**: Defines the root storage path (`./storage`).
- **`get_ffmpeg()` / `get_ffprobe()`**: Returns paths to the FFmpeg binaries.

#### `VideoCreateRequest` (Pydantic Model)

Validates the input payload for creating a video.

- **Fields**: `title`, `script`, `voice`, `image_style`, `scenes_count`, `scenes`.
- **Validation**: Ensures script length (10-5000 chars) and valid resolutions.

#### `ScriptProcessor`

Handles text processing.

- **`split_script(script, target_scenes)`**: Uses heuristics (regex splitting by sentence/punctuation) to divide a long script into roughly equal sized scenes.

#### `VideoGenerator`

The main engine class.

- **`__init__`**: Initializes API clients (OpenAI, Pexels, etc.).
- **`generate_audio(text, language, voice_id)`**: Calls TTS services (specifically looking like a custom "Audixa" wrapper or gTTS fallback) to create audio files.
- **`generate_visual(prompt, style, ...)`**: Orchestrates image generation.
  - Tries multiple providers in order: Replicate -> Stability -> HuggingFace -> Pexels (if photo style) -> Fallback.
- **`create_scene_video(...)`**: Uses FFmpeg to combine a single image + audio + text overlay into a `.mp4` file.
- **`_concatenate_videos(...)`**: Stitches multiple scene videos into the final output.
- **`create_video(project_id, request)`**: Background task pipeline:
  1. Split Logic (if needed).
  2. For each scene: Generate Audio -> Generate Visual -> Create Scene Video.
  3. Concatenate all scenes.
  4. Update Project Status.

### API Endpoints

- **`POST /api/upload/scene-image`**:
  - **Purpose**: Handles user uploads for specific scenes.
  - **Storage**: Saves files to `storage/visuals/` with a `custom_` prefix.
  - **Returns**: URL path to the image.

- **`GET /api/config`**: Returns available voices, styles, and languages.
- **`POST /api/scripts/preview`**: Returns how the script will be split (used by the "Preview Split Scene" button).
- **`POST /api/videos/create`**: Initiates the background generation task.
- **`GET /api/projects/{id}/status`**: Polling endpoint for progress bars.

## 4. Frontend Details (`frontend/index.html`)

### Key Functions

- **`initializeForm()`**: Sets up event listeners for character counting and sliders.
- **`previewScriptSplit()`**:
  - Sends the script to the backend.
  - Receives the JSON list of scenes.
  - Populates the `scenesPreview` variable.
  - user calls `showScriptPreview()`.
- **`showScriptPreview(data)`**:
  - Renders the modal with scene cards.
  - **Features**:
    - Editable text areas.
    - **Image Upload Button**: Calls `uploadSceneImage()`.
- **`uploadSceneImage(index)`**:
  - Takes the file from the hidden input.
  - POSTs it to `/api/upload/scene-image`.
  - Updates the specific scene object in `scenesPreview` with the new `custom_image_url`.
- **`proceedToVoiceSelection()`**: Closes modal and moves to Step 3.
- **`createVideo()`**:
  - Gathers all data (including the modified `scenes` list with custom images).
  - Sends the final payload to `/api/videos/create`.
- **`startProgressPolling()`**: Checks status every 2 seconds until completion.

## 5. Tools & Libraries

- **FFmpeg**:
  - **Purpose**: The core video processing tool.
  - **Usage**: Used to scale images, loop them to match audio duration, draw text overlays, and concatenate video segments.
- **Pillow (PIL)**: Python Image Library. Used for basic image manipulation and text overlay fallbacks if FFmpeg text drawing fails.
- **FastAPI**: The web framework serving the API.
- **Uvicorn**: The ASGI server running the app.
- **Bootstrap 5**: CSS framework for the frontend UI.

## 6. How to Run

1. **Start Backend**:
   ```bash
   cd backend
   python main.py
   # Runs on http://localhost:8001
   ```
2. **Start Frontend**:
   ```bash
   cd frontend
   python -m http.server 3000
   # Runs on http://localhost:3000
   ```
