import uuid
import random
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from utils import logger

def import_questions(parsed_questions: List[Dict], source_filename: str) -> Tuple[Dict[str, Dict], List[str], List[Dict]]:
    """
    Нормализует вопросы, присваивает UUID, фильтрует некорректные.
    Возвращает: (db, id_list, excluded_list)
    """
    logger.info(f"IMPORT_START: Processing {len(parsed_questions)} raw items from {source_filename}")
    
    questions_db = {}
    questions_list = []
    excluded_questions = []
    
    import_time = datetime.now().isoformat()

    for item in parsed_questions:
        # Валидация
        q_text = item.get("question")
        options = item.get("options")
        correct = item.get("correct_text")

        if not q_text or not options or not correct:
            reason = "Missing fields"
            if not options: reason = "Empty options"
            elif not correct: reason = "No correct text identified"
            
            excluded_questions.append({"item": str(item)[:50], "reason": reason})
            continue
            
        # Проверка наличия правильного ответа в опциях (нестрогая, просто check)
        if correct not in options:
             # Можно добавить логику "мягкого" поиска, но по ТЗ исключаем или логируем
             logger.warning(f"Correct answer '{correct}' not found inside options for question: {q_text[:30]}...")

        # Создание ID
        q_id = uuid.uuid4().hex
        
        normalized_q = {
            "id": q_id,
            "question": q_text,
            "options": options,
            "correct_text": correct,
            "meta": {
                "source_filename": source_filename,
                "imported_at": import_time
            }
        }
        
        questions_db[q_id] = normalized_q
        questions_list.append(q_id)

    logger.info(f"IMPORT_END: Imported {len(questions_db)}, Excluded {len(excluded_questions)}")
    return questions_db, questions_list, excluded_questions

def select_questions(questions_db: Dict[str, Dict], 
                     questions_list: List[str],
                     count: int, 
                     seed: Optional[int] = None,
                     restore_signature: Optional[Dict] = None) -> Tuple[List[str], Dict[str, List[int]], int]:
    """
    Выбирает вопросы и перемешивает варианты ответов.
    Если передан restore_signature, восстанавливает точь-в-точь.
    """
    
    # 1. Режим восстановления
    if restore_signature:
        logger.info("Restoring test from signature")
        selected_ids = restore_signature["ids"]
        options_orders = restore_signature["options_orders"]
        used_seed = restore_signature.get("seed", 0)
        return selected_ids, options_orders, used_seed

    # 2. Режим нового теста
    if count > len(questions_list):
        raise ValueError(f"Запрошено {count}, но доступно только {len(questions_list)}")

    if seed is None:
        seed = int(time.time())
    
    rng = random.Random(seed)
    
    # Выбор ID вопросов
    # По ТЗ: случайный выбор без повторов
    # Копируем список, чтобы не менять исходный порядок импорта глобально
    pool = list(questions_list)
    # Если нужно просто выбрать N случайных:
    selected_ids = rng.sample(pool, count)
    
    # Генерация порядка вариантов ответов
    options_orders = {}
    for q_id in selected_ids:
        q_obj = questions_db[q_id]
        n_opts = len(q_obj["options"])
        order = list(range(n_opts))
        rng.shuffle(order)
        options_orders[q_id] = order
        
    return selected_ids, options_orders, seed

def grade_answer(question_obj: Dict, chosen_text: str) -> bool:
    return chosen_text == question_obj["correct_text"]

def get_shuffled_options(question_obj: Dict, order: List[int]) -> List[str]:
    orig = question_obj["options"]

    return [orig[i] for i in order]
