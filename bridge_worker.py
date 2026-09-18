from pathlib import Path
import sys

from fh6_apex5_bridge import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: bridge_worker.py <profile.ini>")
    main(Path(sys.argv[1]))
