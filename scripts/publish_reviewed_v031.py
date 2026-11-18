"""Manual v0.3.1 publisher: reuse the reviewed fail-closed release gate."""
from scripts.publish_reviewed_release import main

if __name__ == "__main__":
    raise SystemExit(main(version="0.3.1"))
