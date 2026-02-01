# Video Generation Pipeline Walkthrough

## 1. Tamil Subtitle Rendering (ASS/libass)

**Goal**: Fix typography issues (dotted circles) and rendering crashes for complex scripts (Tamil, Hindi, Arabic).

**Solution**:

- **Method**: Switched from `drawtext` (unstable) to `.ass` subtitles (industry standard).
- **Implementation**:
  - `ComplexScriptRenderer.generate_ass_file()`: Creates a subtitle file with precise styling.
  - `VideoGenerator`: Uses a two-pass render.
    1.  Generate raw video (Image + Audio).
    2.  Burn subtitles using `ass=filename.ass` filter.
- **Result**: Perfect Tamil text shaping via `libass` + `HarfBuzz`.

## 2. Concatenation Stability & Fixes

**Goal**: Fix `video: null` errors and FFmpeg exit code `4294967274` (EINVAL).

**Problem**:

- **Timeout**: Re-encoding large files exceeded 60s -> Fixed by raising timeout to 300s.
- **EINVAL Error**: `filter_complex` re-encoding failed when concatenating scenes with burned ASS subtitles due to slight metadata/timestamp mismatches.

**Solution**:

- **Adaptive Strategy**:
  - **Simple Scripts**: Uses `filter_complex` (Re-encoding) for consistency.
  - **Complex Scripts (ASS)**: Uses **Concat Demuxer** (`-f concat -c copy`). This avoids re-encoding entirely, bypassing the stream mismatch errors and significantly speeding up processing.
- **Implementation**: Added `_concatenate_with_demuxer` and conditional logic in `create_video`.

## 3. Unified Error Handling Strategy

**Goal**: Eliminate "silent failures".

**Solution**:

- **Structured Errors**: Custom exceptions (`VideoConcatenationError`, `FFmpegError`) map to specific UI messages.
- **Safe Execution**: `run_ffmpeg_safe()` wrapper captures stderr and enforces timeouts.
- **API Response**: Returns specific error codes.

### UI Message Mapping

| Backend Error Code | UI Message                                             | Developer Action                               |
| :----------------- | :----------------------------------------------------- | :--------------------------------------------- |
| `CONCAT_FAILED`    | "Video scenes couldn’t be combined. Please try again." | Check detailed logs in `project.error.details` |
| `TIMEOUT`          | "Processing took too long. Try a shorter script."      | Check rendering resolution/duration.           |
| `RENDERING_FAILED` | "We encountered a technical issue creating the video." | Inspect FFmpeg stderr for specific issues.     |
| `RESOURCE_MISSING` | "A required system file (font/media) is missing."      | specific font or asset failed to load.         |

**Verification**:

- Ran `test_ass_pipeline.py`.
- **Result**: Successfully generated Tamil scenes AND successfully concatenated them using the demuxer.
