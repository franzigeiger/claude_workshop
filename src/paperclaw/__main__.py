import logging
import os
import sys


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("paperclaw")
    log.info("paperclaw scaffold ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
