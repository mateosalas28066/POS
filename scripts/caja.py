"""Lanza el POS. Uso: python scripts/caja.py [pos.db]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from caja.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
