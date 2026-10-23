from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cos-standards")
except PackageNotFoundError:
    __version__ = "0.1.0"
