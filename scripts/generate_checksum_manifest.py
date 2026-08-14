"""Generate the committed SHA-256 manifest for evaluation artifacts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usher_pipeline.output.checksums import create_checksum_manifest


if __name__ == "__main__":
    print(create_checksum_manifest())
