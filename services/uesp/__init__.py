# services/uesp/__init__.py
"""
Everything UESP-specific - fetching, rate limiting, parsing, and
normalization - lives in this package. The rest of services/ stays
app-wide and doesn't know UESP exists; the importer doesn't know the
UI exists.
"""
