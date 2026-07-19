class APIError(Exception):
    """Raised when Binance API request fails."""


class StorageError(Exception):
    """Raised when local file storage fails."""


class UploadError(Exception):
    """Raised when uploading file to S3 fails."""
