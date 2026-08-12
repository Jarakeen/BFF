# services/eso_db/__init__.py
"""
Loads the normalized JSON data/uesp/ produces into a relational
SQLite database (eso.db).

This package is deliberately independent of services/uesp/: it
never imports anything from there, and doesn't know or care whether
a record came from UESP, was hand-written, or came from some other
importer entirely. Its only contract is the JSON shape documented in
data/uesp/README.md. That's the seam between "fetch and normalize
data from a source" and "load normalized data into a database" -
each side can change without the other needing to know.
"""
