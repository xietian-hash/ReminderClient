from __future__ import annotations

import sys

from reminder_client.app import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

