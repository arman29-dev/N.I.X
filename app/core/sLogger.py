from logging import Filter, Formatter, StreamHandler, getLogger
from logging.handlers import RotatingFileHandler
from logging import INFO, WARNING, ERROR

from re import sub, IGNORECASE

from core.config import LOG_DIR



# Creating log directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)

class SensitiveDataFilter(Filter):

    def filter(self, record):
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            # Remove 2FA codes (6 digits)
            msg = sub(r'\b\d{6}\b', '[REDACTED_2FA]', msg)
            # Remove passwords
            msg = sub(r'password["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', 'password=[REDACTED]', msg, flags=IGNORECASE)
            # Remove email patterns in sensitive contexts
            msg = sub(r'(token|key|secret)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', r'\1=[REDACTED]', msg, flags=IGNORECASE)
            record.msg = msg
        return True

def setup_logging():
    # Create formatters
    detailed_formatter = Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    simple_formatter = Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Root logger configuration
    root_logger = getLogger()
    root_logger.setLevel(INFO)

    # Console handler
    console_handler = StreamHandler()
    console_handler.setLevel(INFO)
    console_handler.setFormatter(simple_formatter)

    # File handler for general logs
    file_handler = RotatingFileHandler(
        LOG_DIR / "server.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(INFO)
    file_handler.setFormatter(detailed_formatter)

    # File handler for security logs
    security_handler = RotatingFileHandler(
        LOG_DIR / "security.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    security_handler.setLevel(WARNING)
    security_handler.setFormatter(detailed_formatter)

    # Error handler
    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    file_handler.addFilter(sensitive_filter)
    security_handler.addFilter(sensitive_filter)
    error_handler.addFilter(sensitive_filter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(security_handler)
    root_logger.addHandler(error_handler)

    # Create security logger
    security_logger = getLogger('security')
    security_logger.setLevel(INFO)

    return root_logger, security_logger

# Initialize loggers
logger, security_logger = setup_logging()
