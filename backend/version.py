from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("trove")
except PackageNotFoundError:
    __version__ = "0.0.0dev"

if __name__ == "__main__":
    print(__version__)