"""User-facing errors. CLIs print these and exit 2."""


class StandardsError(Exception):
    """A config, schema, or usage problem. Not a lint finding."""
