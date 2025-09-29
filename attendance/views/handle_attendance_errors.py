"""Module for handling attendance error data."""

import uuid
from io import BytesIO
from urllib.parse import urljoin

import pandas as pd
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def handle_attendance_errors(error_list):
    """
    Reorganize a list of error dictionaries into a structured error data dictionary
    and remove keys with all None values, then store the result using Django's
    configured storage backend.

    Parameters:
        error_list (list[dict]): A list of dictionaries containing error details.

    Returns:
        str: A URL that can be used to download the stored error file.
    """
    error_data = {
        "Badge ID": [],
        "Shift": [],
        "Work type": [],
        "Attendance date": [],
        "Check-in date": [],
        "Check-in": [],
        "Check-out date": [],
        "Check-out": [],
        "Worked hour": [],
        "Minimum hour": [],
        "Badge ID Error": [],
        "Shift Error": [],
        "Work Type Error": [],
        "Check-in Validation Error": [],
        "Check-out Validation Error": [],
        "Attendance Error": [],
        "Attendance Date Validation Error": [],
        "Check-in Error": [],
        "Check-out Error": [],
        "Worked Hours Error": [],
        "Minimum Hour Error": [],
        "Attendance Date Error": [],
        "Check-out Date Error": [],
        "Check-out Date Error": [],
        "Other Errors": [],
    }

    for item in error_list:
        for key, value in error_data.items():
            value.append(item.get(key))

    keys_to_remove = [
        key for key, value in error_data.items() if all(v is None for v in value)
    ]

    for key in keys_to_remove:
        del error_data[key]

    data_frame = pd.DataFrame(error_data, columns=error_data.keys())
    buffer = BytesIO()
    data_frame.to_excel(buffer, index=False)
    buffer.seek(0)

    file_uuid = uuid.uuid4()
    file_name = f"attendance/error_reports/attendance_import_errors_{file_uuid}.xlsx"
    saved_path = default_storage.save(file_name, ContentFile(buffer.getvalue()))
    buffer.close()

    try:
        download_url = default_storage.url(saved_path)
    except Exception:
        media_url = getattr(settings, "MEDIA_URL", "/")
        download_url = saved_path
        if not download_url.startswith(("http://", "https://", "/")):
            download_url = urljoin(media_url, download_url)

    return download_url
