import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="Data Contracts Dashboard", page_icon="📜", layout="wide")

st.title("📜 Data Contracts Dashboard")
st.markdown("Мониторинг статуса контрактов данных.")

RESULTS_FILE = "validation_results.json"

if not os.path.exists(RESULTS_FILE):
    st.warning("⚠️ Файл результатов не найден. Запустите `validate_contract.py` для проверки контракта.")
    st.stop()

with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

# --- ОБЩИЙ СТАТУС ---
st.subheader(f"Контракт: {results['dataset']} (Владелец: {results['owner']})")

if results['columns_ok'] and results['rules_ok']:
    st.success("✅ Все проверки пройдены! Данные соответствуют контракту.")
else:
    st.error("❌ Найдены нарушения контракта!")

st.write(f"**Последняя проверка:** {results['timestamp']}")

# --- КОЛОНКИ ---
st.divider()
st.subheader("Проверка колонок")
for col in results.get("columns", []):
    if col["status"] == "success":
        st.success(f"✅ {col['column']} — найдена")
    else:
        st.error(f"❌ {col['column']} — {col['reason']}")

# --- ПРАВИЛА КАЧЕСТВА ---
st.divider()
st.subheader("Правила качества (Quality Rules)")
for rule in results.get("rules", []):
    if rule["status"] == "success":
        st.success(f"✅ {rule['rule']} ({rule['severity']}) — нарушений нет")
    elif rule["status"] == "failed":
        st.error(f"❌ {rule['rule']} ({rule['severity']}) — {rule['bad_rows']} нарушений")
    else:
        st.warning(f"⚠️ {rule['rule']} — ошибка проверки: {rule.get('error', '')}")

# --- ФУТЕР ---
st.sidebar.info(
    "Этот дашборд читает `validation_results.json`, который создается скриптом `validate_contract.py`. "
    "Запустите валидатор, чтобы обновить данные."
)