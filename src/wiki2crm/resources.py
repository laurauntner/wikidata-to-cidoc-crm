from importlib import resources
from pathlib import Path
from typing import Iterable

def shapes_path(*parts: str) -> Path:
    """Return a pathlib.Path to a file inside the installed shapes directory."""
    base = resources.files(__package__) / "shapes"
    return Path(base) / Path(*parts)
