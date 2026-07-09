"""Разовый запуск сбора из командной строки.

    python -m app.collect            # все источники
    python -m app.collect cbr_press  # один коллектор (по name)
"""
import json
import logging
import sys

from . import db
from .collectors import get_collectors, run_all, run_collector


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    db.init_db()
    if len(sys.argv) > 1:
        wanted = sys.argv[1]
        matches = [c for c in get_collectors() if c.name == wanted]
        if not matches:
            names = ", ".join(c.name for c in get_collectors())
            print(f"Неизвестный коллектор «{wanted}». Доступны: {names}")
            return 1
        results = [run_collector(c) for c in matches]
    else:
        results = run_all()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r["status"] == "ok" for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
