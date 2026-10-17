import os
import re

# Excluded directory names
EXCLUDED_DIRECTORIES = {
    ".git",
    ".github",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "vendor",
    "bower_components",
    "dist",
    "build",
    "out",
    "target",
    "bin",
    "obj",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "coverage",
    ".turbo",
    ".gradle",
}

# Excluded binary and media extensions
EXCLUDED_EXTENSIONS = {
    # Binaries & compiled artifacts
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".class",
    ".pyc",
    ".pyo",
    ".pyd",
    ".o",
    ".obj",
    ".a",
    ".lib",
    ".wasm",
    # Archives & compressed formats
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".jar",
    ".war",
    # Images & icons
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".svg",
    ".tiff",
    ".psd",
    # Audio & video
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    # Fonts
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    # Documents & databases
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".db",
    ".sqlite",
    ".sqlite3",
    # Lockfiles & minified code
    ".min.js",
    ".min.css",
}

# Specific filenames to ignore (lockfiles, generated files, logs)
EXCLUDED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
    "flake.lock",
    "pipfile.lock",
    "npm-debug.log",
    "yarn-debug.log",
    "yarn-error.log",
    ".ds_store",
    "thumbs.db",
}

# Secret filename patterns (credentials, keys, tokens)
SECRET_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pkcs12$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
    re.compile(r"^id_rsa.*$", re.IGNORECASE),
    re.compile(r"^id_ed25519.*$", re.IGNORECASE),
    re.compile(r".*credentials.*\.json$", re.IGNORECASE),
]

# Maximum individual file size in bytes (1 MB default)
DEFAULT_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024


def is_binary_content(content_bytes: bytes) -> bool:
    """Detect if content is binary via null-byte inspection in the first 8 KB."""
    chunk = content_bytes[:8192]
    return b"\x00" in chunk


def should_index_file(
    rel_path: str,
    file_size_bytes: int = 0,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> bool:
    """Determine whether a file should be indexed based on path, extension, and size."""
    # Normalize separators
    normalized_path = rel_path.replace("\\", "/").strip("/")
    parts = normalized_path.split("/")

    # Check directory exclusions
    for dir_part in parts[:-1]:
        if dir_part.lower() in EXCLUDED_DIRECTORIES:
            return False

    filename = parts[-1]
    filename_lower = filename.lower()

    # Check filename exclusions
    if filename_lower in EXCLUDED_FILENAMES:
        return False

    # Check secret filename patterns
    for pattern in SECRET_PATTERNS:
        if pattern.match(filename):
            return False

    # Check extension exclusions
    _, ext = os.path.splitext(filename_lower)
    if ext in EXCLUDED_EXTENSIONS:
        return False

    # Compound extensions like .min.js
    if filename_lower.endswith(".min.js") or filename_lower.endswith(".min.css"):
        return False

    # Check file size limit
    if file_size_bytes > max_size_bytes:
        return False

    return True
