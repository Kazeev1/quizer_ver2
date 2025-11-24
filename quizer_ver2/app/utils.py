import logging
import os
from logging.handlers import RotatingFileHandler
import pandas as pd
from datetime import datetime

def setup_logging():
    log_dir = "app/logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger("quiz_app")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"), 
            maxBytes=5*1024*1024, 
            backupCount=3,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Вывод в консоль для удобства разработки
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    
    return logger

logger = setup_logging()

def convert_to_csv(answers_given: list, seed: int = None) -> bytes:
    """Конвертирует историю ответов в CSV байты (utf-8-sig для Excel)."""
    if not answers_given:
        return b""
    
    # Преобразуем список словарей в DataFrame
    df = pd.DataFrame(answers_given)
    
    # Добавляем seed ко всем строкам для отчетности, если он есть
    if seed is not None:
        df['test_seed'] = seed
    else:
        df['test_seed'] = ''
        
    # Упорядочиваем колонки согласно ТЗ
    cols = ['timestamp', 'test_seed', 'question_id', 'question_text', 'chosen_text', 'correct_text', 'is_correct']
    # Фильтруем только существующие колонки (на случай если структура answers_given будет меняться)
    final_cols = [c for c in cols if c in df.columns]
    
    return df[final_cols].to_csv(index=False).encode('utf-8-sig')