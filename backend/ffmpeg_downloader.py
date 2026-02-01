"""
FFmpeg Downloader with Harfbuzz Support

Automatically downloads and installs FFmpeg with harfbuzz support for complex script rendering.
Uses BtbN's FFmpeg builds which include --enable-libharfbuzz.
"""

import urllib.request
import zipfile
import logging
import os
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# BtbN FFmpeg builds with harfbuzz support
# See: https://github.com/BtbN/FFmpeg-Builds
FFMPEG_DOWNLOAD_URLS = {
    "win64": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "win32": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win32-gpl.zip",
}


def get_system_architecture() -> str:
    """Detect if system is 32-bit or 64-bit Windows."""
    import struct
    if struct.calcsize("P") == 8:
        return "win64"
    else:
        return "win32"


def has_harfbuzz_support(ffmpeg_path: str) -> bool:
    """Check if FFmpeg binary has harfbuzz support."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-buildconf"],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout + result.stderr
        return "libharfbuzz" in output or "harfbuzz" in output.lower()
    except Exception as e:
        logger.warning(f"Could not check FFmpeg harfbuzz support: {e}")
        return False


def download_ffmpeg_with_harfbuzz(ffmpeg_dir: Path) -> bool:
    """
    Download FFmpeg with harfbuzz support from BtbN's builds.
    
    Args:
        ffmpeg_dir: Directory where FFmpeg should be installed
        
    Returns:
        True if download and installation successful, False otherwise
    """
    try:
        ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect architecture
        arch = get_system_architecture()
        url = FFMPEG_DOWNLOAD_URLS.get(arch)
        
        if not url:
            logger.error(f"Unsupported architecture: {arch}")
            return False
        
        logger.info(f"Downloading FFmpeg with harfbuzz support ({arch})...")
        logger.info(f"URL: {url}")
        
        # Download the zip file
        zip_path = ffmpeg_dir / "ffmpeg_latest.zip"
        
        def download_with_progress(url, destination):
            """Download file with progress reporting."""
            try:
                urllib.request.urlretrieve(url, destination)
                logger.info(f"✓ Downloaded: {destination}")
                return True
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return False
        
        if not download_with_progress(url, zip_path):
            return False
        
        # Extract the zip file
        logger.info("Extracting FFmpeg...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # BtbN builds have structure: ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe
                zip_ref.extractall(ffmpeg_dir)
            logger.info("✓ Extracted FFmpeg")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return False
        
        # Find and move ffmpeg.exe to the root ffmpeg_dir/bin/
        logger.info("Installing FFmpeg...")
        extracted_dirs = list(ffmpeg_dir.glob("ffmpeg-master-latest-*"))
        
        if extracted_dirs:
            extracted_dir = extracted_dirs[0]
            bin_dir = extracted_dir / "bin"
            
            # Create bin directory if needed
            ffmpeg_bin_dir = ffmpeg_dir / "bin"
            ffmpeg_bin_dir.mkdir(parents=True, exist_ok=True)
            
            # Move ffmpeg files
            if bin_dir.exists():
                for file in bin_dir.glob("*"):
                    destination = ffmpeg_bin_dir / file.name
                    if destination.exists():
                        destination.unlink()
                    shutil.copy2(file, destination)
                    logger.info(f"  ✓ Installed: {file.name}")
            
            # Clean up extracted directory and zip
            shutil.rmtree(extracted_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
            
            # Verify installation
            ffmpeg_exe = ffmpeg_bin_dir / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                logger.info(f"✓ FFmpeg installed successfully: {ffmpeg_exe}")
                
                # Verify harfbuzz support
                if has_harfbuzz_support(str(ffmpeg_exe)):
                    logger.info("✓ Verified: FFmpeg has harfbuzz support!")
                    return True
                else:
                    logger.warning("⚠ Harfbuzz support not detected in new FFmpeg")
                    logger.info("  Trying anyway - may work with older harfbuzz detection")
                    return True
            else:
                logger.error(f"FFmpeg executable not found after extraction")
                return False
        else:
            logger.error("Could not find extracted FFmpeg directory")
            return False
            
    except Exception as e:
        logger.error(f"FFmpeg download failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def ensure_ffmpeg_has_harfbuzz(ffmpeg_path: str = None) -> bool:
    """
    Ensure FFmpeg has harfbuzz support, downloading if necessary.
    
    Args:
        ffmpeg_path: Path to FFmpeg executable. If None, tries to find in PATH.
        
    Returns:
        True if FFmpeg has harfbuzz support, False otherwise
    """
    if not ffmpeg_path:
        # Try to find FFmpeg in PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            logger.error("FFmpeg not found in PATH")
            return False
    
    # Check current FFmpeg
    if has_harfbuzz_support(ffmpeg_path):
        logger.info("✓ Current FFmpeg has harfbuzz support")
        return True
    
    logger.warning("Current FFmpeg does NOT have harfbuzz support")
    logger.info("Attempting to download FFmpeg with harfbuzz...")
    
    # Get directory of current FFmpeg
    ffmpeg_dir = Path(ffmpeg_path).parent.parent  # Go up from bin/ to ffmpeg root
    
    # Try to download replacement
    if download_ffmpeg_with_harfbuzz(ffmpeg_dir):
        # Verify new FFmpeg
        new_ffmpeg = ffmpeg_dir / "bin" / "ffmpeg.exe"
        if has_harfbuzz_support(str(new_ffmpeg)):
            logger.info("✓ Successfully installed FFmpeg with harfbuzz support!")
            return True
    
    logger.error("Failed to install FFmpeg with harfbuzz support")
    return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the downloader
    import sys
    
    if len(sys.argv) > 1:
        ffmpeg_path = sys.argv[1]
    else:
        ffmpeg_path = None
    
    if ensure_ffmpeg_has_harfbuzz(ffmpeg_path):
        print("\nSuccess: FFmpeg is ready for complex script rendering!")
        sys.exit(0)
    else:
        print("\nError: Failed to ensure harfbuzz support")
        sys.exit(1)
