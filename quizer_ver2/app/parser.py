import streamlit as st
import docx
import io
import random
from typing import List, Dict
from utils import logger

def _parse_quiz_bytes(docx_bytes: bytes) -> List[Dict]:
    """
    Внутренняя логика парсинга:
    Читает байты docx, ищет вопросы (начинаются с №) и ответы (красным цветом).
    """
    try:
        doc = docx.Document(io.BytesIO(docx_bytes))
    except Exception as e:
        logger.error(f"Не удалось открыть docx из байтов: {e}")
        return []

    questions = []
    current_q = None
    RED_HEX = 'FF0000' 

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Начало нового вопроса
        if text.startswith("№"):
            # Если есть предыдущий вопрос и у него найден правильный ответ -> сохраняем
            if current_q and current_q["correct_text"]:
                questions.append(current_q)
            
            # Инициализируем новый вопрос
            current_q = {
                "question": text,
                "options": [],
                "correct_text": None,
                # id генерируется здесь, но в quiz_manager он будет заменен на UUID для уникальности
                "id": random.getrandbits(16) 
            }
        
        # Если мы внутри вопроса, значит это вариант ответа
        elif current_q:
            is_correct = False
            # Проверка runs на наличие красного цвета
            for run in para.runs:
                if run.font.color and run.font.color.rgb and str(run.font.color.rgb) == RED_HEX:
                    is_correct = True
                    break
            
            current_q["options"].append(text)
            
            # Если нашли красный цвет, запоминаем текст как правильный ответ
            if is_correct:
                current_q["correct_text"] = text

    # Не забываем добавить последний вопрос после цикла
    if current_q and current_q["correct_text"]:
        questions.append(current_q)

    return questions

@st.cache_data
def parse_quiz_bytes_cached(docx_bytes: bytes) -> List[Dict]:
    """
    Обертка с кешированием для Streamlit.
    Вызывает логику парсинга.
    """

    return _parse_quiz_bytes(docx_bytes)
