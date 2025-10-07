from importlib.metadata import version, PackageNotFoundError

try:
    from importlib.metadata import version, PackageNotFoundError
except Exception:
    def version(_): return "0+unknown"
    class PackageNotFoundError(Exception): pass

try:
    __version__ = version("wiki2crm")
except PackageNotFoundError:
    __version__ = "0+unknown"