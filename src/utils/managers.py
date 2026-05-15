import logging
import os
from datetime import datetime

class LogManager:
    _logger = None
    _history = []

    @classmethod
    def get_logger(cls):
        if cls._logger is None:
            # Ensure outputs directory exists
            os.makedirs("outputs", exist_ok=True)
            log_file = f"outputs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            logger = logging.getLogger("AI_Flow")
            logger.setLevel(logging.INFO)
            
            # File handler
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.INFO)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter('%(levelname)s - %(asctime)s - [%(name)s] %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(ch)
            
            cls._logger = logger
        return cls._logger

    @classmethod
    def _append_history(cls, level: str, module: str, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = f"[{level} {timestamp}] [{module}] {message}"
        cls._history.append(entry)
        if len(cls._history) > 1000:
            cls._history.pop(0)

    @classmethod
    def get_history(cls):
        return cls._history

    @classmethod
    def info(cls, module: str, message: str):
        cls.get_logger().info(f"[{module}] {message}")
        cls._append_history("INFO", module, message)

    @classmethod
    def warn(cls, module: str, message: str):
        cls.get_logger().warning(f"[{module}] {message}")
        cls._append_history("WARN", module, message)

    @classmethod
    def error(cls, module: str, message: str):
        cls.get_logger().error(f"[{module}] {message}")
        cls._append_history("ERROR", module, message)

class VariableManager:
    _variables = {}

    @classmethod
    def save_variable(cls, key: str, value: str):
        cls._variables[key] = value

    @classmethod
    def load_variable(cls, key: str) -> str:
        return cls._variables.get(key, "")

    @classmethod
    def get_all_variables(cls) -> dict:
        return cls._variables.copy()
