from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("trove")
except PackageNotFoundError:
    __version__ = "0.0.0dev"