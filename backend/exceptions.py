class VideoPipelineError(Exception):
    """Base class for all video pipeline errors"""
    def __init__(self, message, code="INTERNAL_ERROR", technical_details=None, user_action="RETRY"):
        self.message = message
        self.code = code
        self.technical_details = technical_details
        self.user_action = user_action
        super().__init__(self.message)

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "action": self.user_action,
            "details": self.technical_details
        }

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

class StorageError(VideoPipelineError):
    """Disk or permission errors"""
    def __init__(self, message, details=None):
        super().__init__(message, "STORAGE_ERROR", details, "RETRY_LATER")

class AssetDownloadError(VideoPipelineError):
    """External asset download failures"""
    def __init__(self, message, details=None):
        super().__init__(message, "ASSET_DOWNLOAD_ERROR", details, "CHECK_NETWORK")

class VideoConcatenationError(VideoPipelineError):
    """Failures during video concatenation (e.g. timeout, EINVAL)"""
    def __init__(self, message, details=None):
        super().__init__(message, "CONCAT_FAILED", details, "RETRY")
