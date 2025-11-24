import streamlit as st
import time
from datetime import datetime
import parser
import quiz_manager
import ui
import utils

# Настройка страницы
st.set_page_config(page_title="Streamlit Quiz", page_icon="📝")

# --- Инициализация Session State ---
if 'questions_db' not in st.session_state:
    st.session_state.questions_db = {}
if 'questions_list' not in st.session_state:
    st.session_state.questions_list = []
    
# Состояние текущего теста
if 'test_active' not in st.session_state:
    st.session_state.test_active = False
if 'current_test_ids' not in st.session_state:
    st.session_state.current_test_ids = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'answers_given' not in st.session_state:
    st.session_state.answers_given = []
if 'options_orders' not in st.session_state:
    st.session_state.options_orders = {} # {q_id: [0, 2, 1]}
if 'last_test_signature' not in st.session_state:
    st.session_state.last_test_signature = None
    
# Флаг блокировки UI после ответа (чтобы пользователь видел результат перед следующим вопросом)
if 'waiting_for_next' not in st.session_state:
    st.session_state.waiting_for_next = False
if 'last_choice_correct' not in st.session_state:
    st.session_state.last_choice_correct = None


def start_test(count, seed=None, repeat=False):
    try:
        signature = None
        if repeat and st.session_state.last_test_signature:
            signature = st.session_state.last_test_signature
            count = signature['count'] # override count
        
        ids, orders, used_seed = quiz_manager.select_questions(
            st.session_state.questions_db,
            st.session_state.questions_list,
            count,
            seed=seed,
            restore_signature=signature
        )
        
        # Установка состояния
        st.session_state.current_test_ids = ids
        st.session_state.options_orders = orders
        st.session_state.current_index = 0
        st.session_state.answers_given = []
        st.session_state.test_active = True
        st.session_state.waiting_for_next = False
        
        # Сохраняем сигнатуру
        st.session_state.last_test_signature = {
            "ids": ids,
            "options_orders": orders,
            "seed": used_seed,
            "count": count,
            "created_at": datetime.now().isoformat()
        }
        
        utils.logger.info(f"TEST_STARTED: count={count}, seed={used_seed}, repeat={repeat}")
        st.rerun()
        
    except ValueError as e:
        st.error(str(e))

def main():
    ui.render_header()

    # 1. ЗАГРУЗКА ФАЙЛА (Если база пуста или хотим обновить)
    with st.expander("📂 Загрузка базы вопросов", expanded=not bool(st.session_state.questions_db)):
        uploaded_file = ui.render_uploader()
        if uploaded_file:
            bytes_data = uploaded_file.read()
            try:
                parsed_data = parser.parse_quiz_bytes_cached(bytes_data)
                if not parsed_data:
                    st.error("Парсер не нашел вопросов. Проверьте формат (красный цвет или *).")
                else:
                    db, q_list, excluded = quiz_manager.import_questions(parsed_data, uploaded_file.name)
                    
                    if db:
                        st.session_state.questions_db = db
                        st.session_state.questions_list = q_list
                        st.success(f"Успешно загружено {len(db)} вопросов.")
                        if excluded:
                            st.warning(f"Исключено вопросов: {len(excluded)}. См. логи.")
                    else:
                         st.error("Ни один вопрос не прошел валидацию.")
                         
            except Exception as e:
                st.error(f"Ошибка при разборе файла: {e}")

    # Если базы нет, дальше не идем
    if not st.session_state.questions_db:
        st.info("Пожалуйста, загрузите файл для начала работы.")
        return

    total_db = len(st.session_state.questions_db)

    # 2. НАСТРОЙКИ И ЗАПУСК (Если тест не активен)
    if not st.session_state.test_active:
        req_count, show_immediate = ui.render_settings(total_db)
        st.session_state.show_immediate = show_immediate # сохраняем настройку
        
        col_start, col_repeat = st.columns(2)
        
        with col_start:
            if st.button("🚀 Начать новый тест (Random)"):
                start_test(req_count)
        
        with col_repeat:
            disabled_repeat = st.session_state.last_test_signature is None
            if st.button("🔄 Повторить прошлый тест", disabled=disabled_repeat):
                start_test(0, repeat=True) # count игнорируется при repeat
                
    # 3. ПРОЦЕСС ПРОХОЖДЕНИЯ
    else:
        # Получаем данные текущего вопроса
        curr_idx = st.session_state.current_index
        total_test = len(st.session_state.current_test_ids)
        
        # Если вышли за пределы - финиш
        if curr_idx >= total_test:
            csv_bytes = utils.convert_to_csv(
                st.session_state.answers_given, 
                st.session_state.last_test_signature.get('seed')
            )
            ui.render_final_stats(st.session_state.answers_given, total_test, csv_bytes)
            
            if st.button("Закрыть тест"):
                st.session_state.test_active = False
                st.rerun()
            return

        q_id = st.session_state.current_test_ids[curr_idx]
        q_obj = st.session_state.questions_db[q_id]
        
        # Восстанавливаем порядок вариантов
        order = st.session_state.options_orders[q_id]
        shuffled_opts = quiz_manager.get_shuffled_options(q_obj, order)
        
        # Рендер вопроса
        # Ключ виджета меняется с индексом, чтобы сбрасывать выбор
        user_choice = ui.render_question_card(q_obj, shuffled_opts, curr_idx, total_test, key_suffix=q_id)

        # Кнопки действий
        # Если мы ждем перехода к следующему (уже ответили)
        if st.session_state.waiting_for_next:
            
            # Показываем фидбек (если включено)
            if st.session_state.show_immediate:
                is_corr = st.session_state.last_choice_correct
                ui.render_result_feedback(is_corr, q_obj["correct_text"])
            
            if st.button("Следующий вопрос ➡️"):
                st.session_state.current_index += 1
                st.session_state.waiting_for_next = False
                st.session_state.last_choice_correct = None
                st.rerun()
                
        else:
            # Мы еще не ответили
            if st.button("Ответить"):
                if not user_choice:
                    st.warning("Выберите вариант ответа!")
                else:
                    is_correct = quiz_manager.grade_answer(q_obj, user_choice)
                    
                    # Запись ответа
                    st.session_state.answers_given.append({
                        "timestamp": datetime.now().isoformat(),
                        "question_id": q_id,
                        "question_text": q_obj["question"],
                        "chosen_text": user_choice,
                        "correct_text": q_obj["correct_text"],
                        "is_correct": is_correct,
                        "options_order": order
                    })
                    
                    # Переключаем состояние
                    st.session_state.waiting_for_next = True
                    st.session_state.last_choice_correct = is_correct
                    st.rerun()

        # Кнопка принудительного выхода
        st.markdown("---")
        if st.button("❌ Прервать тест"):
            st.session_state.test_active = False
            st.rerun()

if __name__ == "__main__":

    main()
