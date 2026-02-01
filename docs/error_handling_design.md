# Video Generation Pipeline: Error Handling & Reliability Design

## 1. Failure Analysis & UI Mapping

| Failure Point           | Technical Cause                               | Behavior (Current)                                         | Behavior (Target)                              | UI Message                                                                     | Action                  |
| :---------------------- | :-------------------------------------------- | :--------------------------------------------------------- | :--------------------------------------------- | :----------------------------------------------------------------------------- | :---------------------- |
| **Subtitle Generation** | Missing Font File (e.g., `ta` font not found) | Logs Error / Crashes                                       | Catch `FileNotFoundError` → `FontMissingError` | "We couldn't find the font required for Tamil. Please contact support."        | Contact Support         |
| **Subtitle Generation** | ASS File IO Error (Permission/Disk Full)      | Raises `IOError`                                           | Catch → `StorageError`                         | "System is out of space or permissions denied."                                | Retry / Contact Support |
| **Scene Video**         | FFmpeg Timeout (Rendering took > 30s)         | `subprocess.TimeoutExpired` (Silent fail or generic error) | Catch → `SceneRenderingTimeoutError`           | "Scene 3 is too complex to render in time. Try shortening the text."           | Retry / Edit Script     |
| **Scene Video**         | FFmpeg Error (Non-zero exit, corrupt asset)   | Returns `None` / Empty path                                | Catch stderr → `FFmpegRenderingError`          | "We encountered a technical issue while creating Scene 2."                     | Retry                   |
| **Concatenation**       | Timeout (> 300s)                              | Returns `""` (Empty string)                                | Catch → `VideoConcatenationTimeoutError`       | "Combining your video took too long. It might be too long or high-resolution." | Retry (Lower Res)       |
| **Concatenation**       | Empty Output (Success exit code but 0 bytes)  | Logs warning, returns `""`                                 | Check size → `VideoOutputEmptyError`           | "The final video could not be saved."                                          | Retry                   |
| **Audio Generation**    | TTS API Limit / Network Error                 | Returns default/empty audio                                | Catch → `TTSGenerationError`                   | "Voice generation failed due to network issues."                               | Retry                   |
| **Assets**              | Download Failed (Pexels/ImageGen)             | Returns `None`                                             | Catch → `AssetDownloadError`                   | "We couldn't download the background image for Scene 1."                       | Retry                   |

---

## 2. standardized Backend Error Handling

We will introduce a unified exception hierarchy to stop "returning None/Empty strings" and strictly use exceptions for control flow on failure.

### Exception Hierarchy

```python
class VideoPipelineError(Exception):
    """Base class for all video pipeline errors"""
    def __init__(self, message, code="INTERNAL_ERROR", technical_details=None, user_action="RETRY"):
        self.message = message
        self.code = code
        self.technical_details = technical_details
        self.user_action = user_action
        super().__init__(self.message)

class UserInputError(VideoPipelineError):
    """Errors caused by invalid user input (Script too long, bad language)"""
    def __init__(self, message, details=None):
        super().__init__(message, "INVALID_INPUT", details, "FIX_INPUT")

class ResourceMissingError(VideoPipelineError):
    """Missing system resources (Fonts, Files)"""
    def __init__(self, message, details=None):
        super().__init__(message, "RESOURCE_MISSING", details, "CONTACT_SUPPORT")

class FFmpegError(VideoPipelineError):
    """FFmpeg execution failures"""
    def __init__(self, message, details=None):
        super().__init__(message, "RENDERING_FAILED", details, "RETRY")

class TimeOutError(VideoPipelineError):
    """Operation timed out"""
    def __init__(self, message, details=None):
        super().__init__(message, "TIMEOUT", details, "RETRY_SIMPLER")
```

### Safe FFmpeg Wrapper Pattern

```python
async def run_ffmpeg_safe(cmd: list, timeout: int = 60, context: str = "operation") -> str:
    """
    Executes FFmpeg with safety rails.
    1. Captures stderr
    2. Enforces timeout
    3. Checks output file existence
    4. Raises typed exceptions (No swallowing errors!)
    """
    try:
        logging.info(f"Starting FFmpeg: {context}")
        # Use a larger buffer or temp file for stderr to avoid deadlocks
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            # Parse stderr for common errors
            error_msg = f"FFmpeg exited with code {result.returncode}"
            details = result.stderr[-1000:] # Last 1000 chars

            if "No such file or directory" in details:
                raise ResourceMissingError("Input file missing during rendering", details)
            if "Permission denied" in details:
                raise VideoPipelineError("Permission denied writing output", "STORAGE_ERROR", details)

            raise FFmpegError(error_msg, details)

        return result.stderr # FFmpeg usually logs stats to stderr, which is fine

    except subprocess.TimeoutExpired:
        raise TimeOutError(f"FFmpeg timed out after {timeout}s", f"Context: {context}")

    except Exception as e:
        if isinstance(e, VideoPipelineError): raise e
        raise VideoPipelineError(f"Unexpected error: {str(e)}", "UNKNOWN_ERROR")
```

---

## 3. API Response Structure

The API should never return `video: null` blindly. It should return a definitive status.

**Success Response:**

```json
{
  "status": "completed",
  "progress": 100,
  "video_url": "/storage/videos/final_123.mp4",
  "error": null
}
```

**Failure Response:**

```json
{
  "status": "failed",
  "progress": 45,
  "video_url": null,
  "error": {
    "code": "RENDERING_FAILED",
    "message": "We encountered a technical issue while creating Scene 2.",
    "action": "RETRY",
    "details": "FFmpeg exit code 1: [Parsed_ass_0 @ 0000...] Shaper: FriBiDi 1.0.10 (SIMPLE)..."
  }
}
```

---

## 4. UI Message Mapping (Frontend)

The Frontend should map `error.code` to friendly toasts/modals.

| Error Code             | Short UI Message                                                       | Suggested Icon |
| :--------------------- | :--------------------------------------------------------------------- | :------------- |
| `INVALID_INPUT`        | "Please check your script length or settings."                         | ⚠️ (Warning)   |
| `RESOURCE_MISSING`     | "A system component (Font/File) is missing. Please contact support."   | 🔧 (Tool)      |
| `RENDERING_FAILED`     | "Video creation failed. Please try again."                             | ❌ (Error)     |
| `TIMEOUT`              | "The process took too long. Try a shorter script or lower resolution." | ⏱️ (Clock)     |
| `STORAGE_ERROR`        | "Server storage error. Please try again later."                        | 💾 (Disk)      |
| `ASSET_DOWNLOAD_ERROR` | "Could not download images/audio. Check your internet?"                | 🌐 (Globe)     |
