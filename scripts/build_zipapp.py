"""Build miscree as one self-contained executable file.

    python3 scripts/build_zipapp.py OUTPUT
"""
import sys
import zipapp
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def build(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    zipapp.create_archive(
        SRC,
        output,
        interpreter="/usr/bin/env python3",
        main="miscree.cli:run",
        filter=lambda path: "__pycache__" not in path.parts,
        compressed=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(Path(sys.argv[1]))
