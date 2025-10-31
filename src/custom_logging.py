# src/custom_logging.py
import logging
import os
import re
from flask_socketio import SocketIO

# SocketIO wird beim Init gesetzt
socketio: SocketIO | None = None

# Eigene Log-Level
LOADING = 24
SUCCESS = 25
logging.addLevelName(LOADING, "LOADING")
logging.addLevelName(SUCCESS, "SUCCESS")


if not os.path.exists("logs"):
    os.mkdir("logs")


def loading(self, message, *args, **kwargs):
    if self.isEnabledFor(LOADING):
        self._log(LOADING, message, args, **kwargs)


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS):
        self._log(SUCCESS, message, args, **kwargs)


logging.Logger.loading = loading
logging.Logger.success = success

# Regex zum Entfernen von ANSI-Escape-Sequenzen
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def strip_ansi(s: str) -> str:
    """Entferne ANSI-Farbcodes aus einem String."""
    if not isinstance(s, str):
        return s
    return _ANSI_RE.sub('', s)


#
# Formatters
#
class ColoredFormatter(logging.Formatter):
    """
    Formatter mit ANSI-Farben für die Konsole.
    """
    green = "\033[1;92m"
    yellow = "\033[1;93m"
    red = "\033[1;31m"
    purple = "\033[1;35m"
    blue = "\033[1;94m"
    reset = "\033[0m"
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    FORMATS = {
        logging.DEBUG: blue + fmt + reset,
        logging.INFO: blue + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
        logging.CRITICAL: red + fmt + reset,
        LOADING: purple + fmt + reset,
        SUCCESS: green + fmt + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.fmt)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class PlainFormatter(logging.Formatter):
    """
    Plain formatter ohne ANSI-Codes (für WebSocket/SSE-Ausgabe).
    """
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    def __init__(self):
        super().__init__(self.fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        # Verwende gewöhnliche Formatierung (ohne Farben)
        return super().format(record)


#
# WebSocket-Handler
#
def init_logger_socketio(app_socketio: SocketIO):
    """SocketIO für Logger initialisieren (call this from your app)."""
    global socketio
    socketio = app_socketio


# Regex: erkennt Log-Level Wörter
_LEVEL_RE = re.compile(r'\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|LOADING|SUCCESS)\b', re.IGNORECASE)
# Regex: erkennt typische Beginn eines Log-Eintrags mit Datum "YYYY-MM-DD "
_TIMESTAMP_SPLIT_RE = re.compile(r'(?=\d{4}-\d{2}-\d{2}\s)')

class WebSocketHandler(logging.Handler):
    """Custom Log Handler der Logs via WebSocket sendet (plain text, no ANSI).
       Splittet zusammengesetzte Nachrichten in einzelne Einträge und sendet für jede Zeile
       das erkannte Log-Level mit.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if not socketio:
                return

            # Formatiere die Nachricht (plain, ohne ANSI)
            msg = self.format(record)
            payload_text = strip_ansi(msg)  # du hattest diese Funktion bereits

            source = record.name
            ts = record.created

            # 1) Splitte nach erkannten Zeitstempel-Beginn (falls vorhanden)
            parts = _TIMESTAMP_SPLIT_RE.split(payload_text)
            # Falls hier eine leere erste part kann auftreten, filtere leere strings
            parts = [p for p in (p.strip() for p in parts) if p]

            # Falls das Split kein Ergebnis liefert (kein Timestamp-Format), treat as single entry
            if not parts:
                parts = [payload_text]

            # 2) Für jede Teilnachricht: Level erkennen, ansonsten fallback auf record.levelname
            for part in parts:
                # Suche erstes Level-Wort in der Zeile
                m = _LEVEL_RE.search(part)
                if m:
                    detected_level = m.group(1).upper()
                else:
                    # fallback: nutze das Level des logging-records (z.B. INFO)
                    detected_level = record.levelname.upper() if record.levelname else 'INFO'

                # Trim und sichere Länge (optional)
                text = part.rstrip('\n')

                # 3) Emit an Clients (ohne broadcast-Keyword — Socket.IO broadcastet an alle wenn kein to/room)
                socketio.emit('log_output', {
                    'text': text,
                    'level': detected_level,
                    'source': source,
                    'timestamp': ts
                })

        except Exception as e:
            # Fehler sichtbar machen (während der Entwicklung)
            print(f"[WebSocketHandler] emit error: {e}")
            self.handleError(record)

#
# Logger-Setup-Funktion
#
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Erzeuge/konfiguriere einen Logger mit:
     - ConsoleHandler (farbig)
     - WebSocketHandler (plain)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Vermeide doppelte Handler wenn mehrmals setup_logger aufgerufen wird
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console (mit Farben)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())

    # WebSocket (ohne Farben)
    websocket_handler = WebSocketHandler()
    websocket_handler.setLevel(level)
    websocket_handler.setFormatter(PlainFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(websocket_handler)

    # Optional: file handler etc. hier hinzufügen

    # Verhindern, dass Log-Nachrichten noch weiter an root-Logger gehen
    logger.propagate = False

    return logger
