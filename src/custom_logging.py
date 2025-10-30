import logging
import os
from flask_socketio import SocketIO

# Flask SocketIO initialisieren
socketio = None

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

logging.basicConfig(level=logging.INFO)


class CustomFormatter(logging.Formatter):
    green = "\033[1;92m"
    yellow = "\033[1;93m"
    red = "\033[1;31m"
    purple = "\033[1;35m"
    blue = "\033[1;94m"
    reset = "\033[0m"
    format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s "

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + format + reset,
        LOADING: purple + format + reset,
        SUCCESS: green + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)




def init_logger_socketio(app_socketio):
    """SocketIO für Logger initialisieren"""
    global socketio
    socketio = app_socketio

class WebSocketHandler(logging.Handler):
    """Custom Log Handler der Logs via WebSocket sendet"""
    
    def emit(self, record):
        try:
            if socketio:
                log_entry = self.format(record)
                socketio.emit('log_output', {
                    'data': log_entry,
                    'level': record.levelname,
                    'source': 'py_main',
                    'timestamp': record.created
                })
        except Exception:
            pass  # Fallback falls WebSocket nicht verfügbar

class CustomFormatter(logging.Formatter):
    """Dein bestehender Formatter"""
    def format(self, record):
        # Deine bestehende Format-Logik
        return super().format(record)

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = False
    
    # Console Handler (dein bestehender)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    
    # WebSocket Handler (neu)
    websocket_handler = WebSocketHandler()
    websocket_handler.setFormatter(CustomFormatter())
    
    # Beide Handler hinzufügen
    logger.addHandler(console_handler)
    logger.addHandler(websocket_handler)
    
    return logger