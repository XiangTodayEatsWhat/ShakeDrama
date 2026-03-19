"""
全局日志配置模块

在应用启动时调用 setup_logging() 来配置日志系统。
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    console: bool = True,
    file: bool = True
):
    """
    配置全局日志系统
    
    Args:
        log_dir: 日志文件目录
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: 是否输出到控制台
        file: 是否输出到文件
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 日志格式
    console_format = '%(levelname)s [%(name)s] %(message)s'
    file_format = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'
    
    # 根logger配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除已有的handlers
    root_logger.handlers.clear()
    
    # 控制台handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(console_format))
        root_logger.addHandler(console_handler)
    
    # 文件handler
    if file:
        # 主日志文件
        log_file = log_path / f"drama_agent_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(file_format))
        root_logger.addHandler(file_handler)
        
        # 错误日志文件
        error_log_file = log_path / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(file_format))
        root_logger.addHandler(error_handler)
    
    # 记录启动信息
    logging.info("=" * 60)
    logging.info("日志系统已初始化")
    logging.info(f"日志级别: {level}")
    logging.info(f"日志目录: {log_path.absolute()}")
    logging.info("=" * 60)

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    使用方式:
        from setup_logging import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    """
    return logging.getLogger(name)

# 便捷函数:为特定模块设置日志级别
def set_module_log_level(module_name: str, level: str):
    """设置特定模块的日志级别"""
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, level.upper()))
    logging.info(f"模块 {module_name} 日志级别设为 {level}")

# 示例用法
if __name__ == '__main__':
    # 初始化日志系统
    setup_logging(level="DEBUG")
    
    # 创建logger
    logger = get_logger(__name__)
    
    # 测试各级别日志
    logger.debug("这是DEBUG级别日志")
    logger.info("这是INFO级别日志")
    logger.warning("这是WARNING级别日志")
    logger.error("这是ERROR级别日志")
    
    # 测试异常日志
    try:
        1 / 0
    except Exception as e:
        logger.error("发生错误", exc_info=True)  # exc_info=True 会记录完整堆栈
    
    print("\n✅ 日志测试完成,请检查 logs/ 目录")
