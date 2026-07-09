"""Настройки приложения. Все параметры переопределяются переменными окружения."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "news.db"))
FRONTEND_DIR = BASE_DIR / "frontend"

# Интервал сбора: по ТЗ каждые 5–10 минут
COLLECT_INTERVAL_MINUTES = int(os.environ.get("COLLECT_INTERVAL_MINUTES", "7"))

HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "25"))
USER_AGENT = os.environ.get(
    "USER_AGENT",
    "MacroNewsMonitor/1.0 (+https://github.com/dmitrynnnnn23/monitoring_news)",
)

# Дополнительный CA-сертификат (PEM). Нужен для rosstat.gov.ru, чей сертификат
# выпущен УЦ «Russian Trusted Root CA» (Минцифры) и не входит в стандартные
# хранилища доверия. Файл объединяется со стандартным бандлом — проверка TLS
# никогда не отключается.
EXTRA_CA_FILE = os.environ.get("EXTRA_CA_FILE", "")

# Отключение источников: DISABLED_SOURCES="tass,interfax"
DISABLED_SOURCES = {
    s.strip() for s in os.environ.get("DISABLED_SOURCES", "").split(",") if s.strip()
}

# Дополнительные RSS-источники (например, лицензированная лента Reuters):
# EXTRA_RSS_SOURCES='[{"id":"reuters","title":"Reuters","url":"https://...","verified":false}]'
EXTRA_RSS_SOURCES = os.environ.get("EXTRA_RSS_SOURCES", "")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Для тестов и разовых запусков: DISABLE_SCHEDULER=1
DISABLE_SCHEDULER = os.environ.get("DISABLE_SCHEDULER", "") == "1"
