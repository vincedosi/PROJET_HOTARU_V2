"""
Logging structuré avec contexte - Remplace 100+ print() et callback dispersés
"""
import sys
import logging
from typing import Optional, Callable, Any
from datetime import datetime


class ContextLogger:
    """Logger avec contexte audit (audit_id, user_email, etc.)."""

    def __init__(
        self,
        name: str = "hotaru",
        audit_id: Optional[str] = None,
        user_email: Optional[str] = None,
        callback: Optional[Callable[[str], None]] = None,
        verbose: bool = False,
    ):
        """
        Initialise le logger.

        Args:
            name: Nom du logger
            audit_id: ID de l'audit (pour traçabilité)
            user_email: Email utilisateur (pour traçabilité)
            callback: Fonction de callback pour les logs (ex: st.write)
            verbose: Mode verbose (logs DEBUG)
        """
        self.audit_id = audit_id
        self.user_email = user_email
        self.callback = callback
        self.verbose = verbose
        self.logs_buffer = []

        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    def _format_message(self, level: str, message: str) -> str:
        """Formate un message avec contexte."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        context_parts = [timestamp]

        if self.audit_id:
            context_parts.append(f"[{self.audit_id[:8]}]")
        if self.user_email:
            context_parts.append(f"[{self.user_email.split('@')[0]}]")

        level_str = f"[{level}]" if level != "INFO" else ""
        context = " ".join(filter(None, context_parts + [level_str]))

        return f"{context} {message}" if context else message

    def info(self, message: str, **kwargs):
        """Log au niveau INFO."""
        formatted = self._format_message("INFO", message)
        self._output(formatted)
        self.logger.info(formatted, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log au niveau DEBUG (seulement si verbose)."""
        if self.verbose:
            formatted = self._format_message("DEBUG", message)
            self._output(formatted, level="debug")
            self.logger.debug(formatted, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log au niveau WARNING."""
        formatted = self._format_message("⚠️ WARNING", message)
        self._output(formatted)
        self.logger.warning(formatted, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log au niveau ERROR."""
        formatted = self._format_message("❌ ERROR", message)
        self._output(formatted)
        self.logger.error(formatted, extra=kwargs)

    def _output(self, message: str, level: str = "info"):
        """Affiche le message via stdout et callback."""
        print(message, file=sys.stdout, flush=True)
        self.logs_buffer.append(message)

        # Callback Streamlit si fourni
        if self.callback:
            self.callback(message)

    def get_logs(self, limit: int = 100) -> list:
        """Récupère les logs récents."""
        return self.logs_buffer[-limit:]

    def clear_logs(self):
        """Vide le buffer de logs."""
        self.logs_buffer.clear()


# Global logger (contexte par défaut)
_default_logger: Optional[ContextLogger] = None


def get_logger(
    audit_id: Optional[str] = None,
    user_email: Optional[str] = None,
    callback: Optional[Callable] = None,
) -> ContextLogger:
    """Récupère ou crée un logger avec contexte."""
    global _default_logger
    if _default_logger is None:
        _default_logger = ContextLogger(
            audit_id=audit_id,
            user_email=user_email,
            callback=callback,
        )
    return _default_logger


def set_default_logger(logger: ContextLogger):
    """Définit le logger par défaut global."""
    global _default_logger
    _default_logger = logger


# Shorthand functions
def log_info(message: str):
    """Shorthand pour logger.info()."""
    logger = get_logger()
    logger.info(message)


def log_debug(message: str):
    """Shorthand pour logger.debug()."""
    logger = get_logger()
    logger.debug(message)


def log_warning(message: str):
    """Shorthand pour logger.warning()."""
    logger = get_logger()
    logger.warning(message)


def log_error(message: str):
    """Shorthand pour logger.error()."""
    logger = get_logger()
    logger.error(message)


__all__ = [
    "ContextLogger",
    "get_logger",
    "set_default_logger",
    "log_info",
    "log_debug",
    "log_warning",
    "log_error",
]
