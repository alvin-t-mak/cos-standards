from importlib.metadata import PackageNotFoundError, version

STANDARDS_VERSION = "0.2.0"

try:
    __version__ = version("cos-standards")
except PackageNotFoundError:
    __version__ = STANDARDS_VERSION
