from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("qumea-plugin")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"