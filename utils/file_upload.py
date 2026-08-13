import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_MIME_PREFIXES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "pdf": (b"%PDF",),
}


def allowed_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def _detect_extension(header):
    for extension, signatures in ALLOWED_MIME_PREFIXES.items():
        for signature in signatures:
            if header.startswith(signature):
                return "jpg" if extension == "jpeg" else extension
    return None


def save_receipt(file_storage):
    """Save an uploaded receipt and return the relative static path."""
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    if not original_name or original_name in (".", ".."):
        raise ValueError("Invalid filename.")

    if not allowed_extension(original_name):
        raise ValueError("Invalid file type. Allowed: PNG, JPG, JPEG, PDF.")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    if size <= 0:
        raise ValueError("Uploaded file is empty.")
    if size > max_size:
        raise ValueError("File exceeds the 5 MB upload limit.")

    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    detected_ext = _detect_extension(header)
    if not detected_ext:
        raise ValueError("File content does not match an allowed receipt type.")

    declared_ext = original_name.rsplit(".", 1)[1].lower()
    normalized_declared = "jpg" if declared_ext == "jpeg" else declared_ext
    if detected_ext != normalized_declared and not (detected_ext == "jpg" and normalized_declared == "jpeg"):
        raise ValueError("File extension does not match file content.")

    unique_name = f"{uuid.uuid4().hex}.{detected_ext if detected_ext != 'jpg' else 'jpg'}"
    upload_dir = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    os.makedirs(upload_dir, exist_ok=True)

    absolute_path = os.path.realpath(os.path.join(upload_dir, unique_name))
    if not absolute_path.startswith(upload_dir + os.sep):
        raise ValueError("Invalid upload path.")

    if os.path.exists(absolute_path):
        raise ValueError("Upload conflict. Please try again.")

    file_storage.save(absolute_path)
    return f"uploads/{unique_name}"
