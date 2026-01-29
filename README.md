# Faceless Video Creator

An automated video creation tool that generates short-form videos from text scripts with AI-generated visuals, text-to-speech audio, and text overlays.

## Features

- **Automatic Script Splitting**: Converts your script into multiple scenes automatically
- **Multiple Voice Options**: 13 different voices with various accents (American, British, Australian)
- **AI-Powered Visuals**:
  - AI image generation (Replicate SDXL, Stability AI, HuggingFace)
  - Pexels photo search for realistic imagery
  - Fallback gradient backgrounds
- **7 Image Styles**: Default, Pixar Art, Anime, Comic, Lego, Cinematic, Pexels Photo
- **Text Overlays**: Automatic text overlay on each scene
- **Multi-Language Support**: 11 languages including English, Spanish, French, German, Italian, Portuguese, Hindi, Arabic, Chinese, Japanese, and Korean
- **Multiple Resolutions**: 720x1280, 1080x1920, 1440x2560

## Prerequisites

- **Python 3.8+**
- **FFmpeg**: Must be installed and accessible
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH or place at `C:\ffmpeg\bin\`
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd shortvideo_maker
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```env
OPENROUTER_API_KEY=your_openrouter_key
STABILITY_API_KEY=your_stability_key
HUGGINGFACE_TOKEN=your_huggingface_token
REPLICATE_API_TOKEN=your_replicate_token
PEXELS_API_KEY=your_pexels_key
```

**Note**: You need at least one AI image generation API key (Replicate, Stability AI, or HuggingFace) OR the Pexels API key for visuals.

## Running the Application

### Start Backend Server

```bash
cd backend
python main.py
```

The backend will start on `http://localhost:8001`

### Start Frontend Server

```bash
cd frontend
python -m http.server 3000
```

The frontend will be available at `http://localhost:3000`

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter your video details:
   - **Title**: Name for your video project
   - **Script**: Your full script (will be auto-split into scenes)
   - **Language**: Select from 11 supported languages
   - **Voice**: Choose from 13 different voice options
   - **Image Style**: Select visual style (Default, Pixar, Anime, etc.)
   - **Resolution**: Choose video resolution
   - **Number of Scenes**: 4-16 scenes
3. Click "Create Video"
4. Monitor progress and download when complete

## API Endpoints

- `GET /api/config` - Get available voices, styles, languages
- `POST /api/videos/create` - Create a new video
- `GET /api/projects/{project_id}/status` - Check video generation status
- `POST /api/visuals/preview` - Preview visual generation
- `POST /api/audio/preview` - Preview audio generation
- `POST /api/scripts/preview` - Preview script splitting

## Project Structure

```
shortvideo_maker/
├── backend/
│   ├── main.py              # Main FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # Environment variables (create this)
│   └── storage/             # Generated assets (auto-created)
│       ├── audio/
│       ├── visuals/
│       ├── scenes/
│       └── videos/
└── frontend/
    └── index.html           # Web interface
```

## Troubleshooting

### FFmpeg Not Found

If you get "WinError 2" or "ffmpeg not found":

- Ensure FFmpeg is installed
- On Windows, place FFmpeg at `C:\ffmpeg\bin\ffmpeg.exe` or add to PATH
- Restart the backend server after installation

### No Visuals Generated

- Check that at least one API key is configured in `.env`
- For Pexels, ensure you have a valid API key from [pexels.com/api](https://www.pexels.com/api/)
- Check backend logs for specific errors

### Audio Issues

- Ensure `gTTS` is installed: `pip install gtts`
- Check internet connection (gTTS requires online access)

## API Keys

Get your API keys from:

- **Replicate**: [replicate.com](https://replicate.com)
- **Stability AI**: [stability.ai](https://stability.ai)
- **HuggingFace**: [huggingface.co](https://huggingface.co)
- **Pexels**: [pexels.com/api](https://www.pexels.com/api/)

## License

This project is for educational and personal use.

## Image Storage Location

**Where are uploaded images stored?**
All user-uploaded images and generated visuals are stored in the backend under:
`backend/storage/visuals/`

- **Uploads**: User uploads are saved here with a `custom_` prefix (e.g., `custom_a1b2c3d4.png`).
- **Generations**: AI-generated images are also saved here.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
