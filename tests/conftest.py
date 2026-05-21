"""Pytest config: force stub mode for every test."""

import os

os.environ.setdefault("GEMINI_ELASTIC_STUB", "1")
