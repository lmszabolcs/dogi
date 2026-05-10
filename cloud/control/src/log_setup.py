import logging
import os


def get_logger(name='dogi'):
    log_dir = '/tmp/dogi_logs'
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(f'{log_dir}/dogi.log', mode='a', encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(name)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
