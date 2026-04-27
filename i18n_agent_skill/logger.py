import logging

from pythonjsonlogger import json


def setup_logger():
    """
    Configure structured JSON logging.
    Suitable for ELK, Datadog, and other log management systems.
    """
    logger = logging.getLogger("i18n_agent_skill")
    log_handler = logging.StreamHandler()

    # Define output fields
    formatter = json.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    return logger


# Global instance
structured_logger = setup_logger()
