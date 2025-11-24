import streamlit as st
import quiz_manager

def render_header():
    st.title("📝 Тестирование (Streamlit Quiz)")

def render_uploader():
    return st.file_uploader("Загрузите .docx с вопросами", type=["docx"])

def render_settings(total_questions: int):
    st.markdown("### Настройки теста")
    col1, col2 = st.columns(2)
    
    with col1:
        requested_count = st.number_input(
            "Количество вопросов", 
            min_value=1, 
            max_value=total_questions, 
            value=min(10, total_questions)
        )
    
    with col2:
        show_immediate = st.checkbox("Показывать правильный ответ сразу", value=True)
        
    return requested_count, show_immediate

def render_question_card(q_data, options, current_idx, total, key_suffix):
    """
    Рендерит область вопроса. Возвращает выбранный вариант (или None).
    """
    # Прогресс
    progress_val = (current_idx) / total
    st.progress(progress_val)
    st.caption(f"Вопрос {current_idx + 1} из {total}")
    
    st.markdown(f"### {q_data['question']}")
    
    # Radio button
    # ВАЖНО: index=None чтобы выбор сбрасывался при смене вопроса, 
    # если мы используем уникальный key для каждого вопроса.
    choice = st.radio(
        "Выберите вариант:", 
        options=options, 
        index=None, 
        key=f"radio_{key_suffix}" 
    )
    
    return choice

def render_result_feedback(is_correct: bool, correct_text: str):
    if is_correct:
        st.success(f"**Правильно!**")
    else:
        st.error(f"**Неверно.**")
        st.markdown(f"Правильный ответ: **{correct_text}**")

def render_final_stats(answers: list, total: int, csv_data: bytes):
    st.markdown("---")
    st.header("🏁 Результаты теста")
    
    correct_count = sum(1 for a in answers if a['is_correct'])
    score_pct = (correct_count / total) * 100 if total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Правильно", correct_count)
    col2.metric("Ошибки", total - correct_count)
    col3.metric("Результат", f"{score_pct:.1f}%")
    
    # Таблица деталей
    if answers:
        st.subheader("Детализация")
        # Простой вывод, можно заменить на dataframe
        for i, ans in enumerate(answers):
            status_icon = "✅" if ans['is_correct'] else "❌"
            with st.expander(f"{status_icon} Вопрос {i+1}: {ans['question_text'][:50]}..."):
                st.write(f"**Ваш ответ:** {ans['chosen_text']}")
                st.write(f"**Правильный:** {ans['correct_text']}")
    
    # Скачивание
    timestamp = answers[0]['timestamp'].replace(':', '-') if answers else "results"
    fname = f"quiz_results_{timestamp}.csv"
    
    st.download_button(
        label="📥 Скачать результаты (CSV)",
        data=csv_data,
        file_name=fname,
        mime="text/csv"
    )
    
    if st.button("Начать заново (сброс сессии)"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
