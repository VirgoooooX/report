"""Shared filesystem paths for local and Docker runtime data."""

import os

BACKEND_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(BACKEND_DIR)

RAWDATA_DIR = os.environ.get('REPORT_RAWDATA_DIR') or os.path.join(BASE_DIR, 'rawdata')
DB_DIR = os.environ.get('REPORT_DB_DIR') or os.path.join(BASE_DIR, 'db')
UPLOAD_DIR = os.environ.get('REPORT_UPLOAD_DIR') or os.path.join(RAWDATA_DIR, 'uploads')
DB_PATH = os.environ.get('REPORT_DB_PATH') or os.path.join(DB_DIR, 'report.db')


def ensure_runtime_dirs():
    os.makedirs(RAWDATA_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def iter_rawdata_files():
    if not os.path.isdir(RAWDATA_DIR):
        return
    for root, dirs, files in os.walk(RAWDATA_DIR):
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and d not in {'__pycache__'}
        ]
        for fname in files:
            yield fname, os.path.join(root, fname)


def find_rawdata_file(filename):
    target = os.path.basename(str(filename or ''))
    if not target:
        return None
    for fname, path in iter_rawdata_files():
        if fname == target:
            return path
    return None
