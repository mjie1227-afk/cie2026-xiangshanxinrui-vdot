"""Compatibility entry point; preparation now uses included sources without network."""
from prepare_sources import main
if __name__ == "__main__":
    raise SystemExit(main())
