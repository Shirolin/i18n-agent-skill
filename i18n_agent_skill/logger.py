import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(name: str = "i18n-agent"):
    """
    配置皇冠级结构化 JSON 日志。
    适配 ELK、Datadog 等企业级日志系统。
    """
    logger = logging.getLogger(name)
    logHandler = logging.StreamHandler(sys.stdout)
    
    # 定义输出字段，包含时间、级别、TraceID 等云原生必备字段
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(levelname)s %(name)s %(message)s %(trace_id)s %(duration_ms)s'
    )
    
    logHandler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    return logger

# 全局实例
structured_logger = setup_logger()
