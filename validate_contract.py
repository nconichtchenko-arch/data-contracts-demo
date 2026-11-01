import yaml
import os
import sys
import psycopg2
from datetime import datetime

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "dwh_marketplace"
DB_USER = "dwh_user"
DB_PASSWORD = "dwh_password"

CONTRACT_PATH = "contracts/fct_sales_contract.yml"

def load_contract(path):
    """Загружает YAML-контракт."""
    if not os.path.exists(path):
        print(f"❌ Файл контракта не найден: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_table_columns(conn, schema, table):
    """Получает реальные колонки и типы из БД."""
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(query, (schema, table))
        return {row[0]: row[1] for row in cur.fetchall()}

def validate_columns(conn, contract):
    """Проверяет, что все колонки из контракта существуют в БД."""
    schema = contract["dataset"]["schema"]
    table = contract["dataset"]["name"]
    
    print(f"\n🔍 Проверка колонок для {schema}.{table}...")
    
    actual_columns = get_table_columns(conn, schema, table)
    if not actual_columns:
        print(f"❌ Таблица {schema}.{table} не найдена в БД.")
        return False
    
    errors = 0
    for col in contract["columns"]:
        col_name = col["name"]
        if col_name not in actual_columns:
            print(f"  ❌ Колонка '{col_name}' отсутствует в БД.")
            errors += 1
        else:
            print(f"  ✅ Колонка '{col_name}' найдена (тип в БД: {actual_columns[col_name]}).")
    
    return errors == 0

def validate_rules(conn, contract):
    """Проверяет правила качества (quality_rules)."""
    schema = contract["dataset"]["schema"]
    table = contract["dataset"]["name"]
    
    print(f"\n🔍 Проверка правил качества для {schema}.{table}...")
    
    errors = 0
    for rule in contract.get("quality_rules", []):
        rule_name = rule["name"]
        column = rule["column"]
        rule_expr = rule["rule"]
        severity = rule["severity"]
        
        # Преобразуем правило в SQL (простая замена value на колонку)
        # Например, "value >= 0" -> "total_revenue >= 0"
        sql_condition = rule_expr.replace("value", column)
        
        # Специальная обработка для matches (регулярка)
        if "matches" in sql_condition:
            # Извлекаем регулярку и заменяем на SQL-оператор ~
            import re
            match = re.search(r"matches\s+'([^']+)'", sql_condition)
            if match:
                pattern = match.group(1)
                sql_condition = f"{column} ~ '{pattern}'"
        
        query = f"SELECT COUNT(*) FROM {schema}.{table} WHERE NOT ({sql_condition});"
        
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                bad_rows = cur.fetchone()[0]
                
                if bad_rows > 0:
                    print(f"  ❌ [{severity.upper()}] {rule_name}: {bad_rows} строк нарушают правило ({sql_condition}).")
                    errors += 1
                else:
                    print(f"  ✅ {rule_name}: нарушений нет.")
        except Exception as e:
            print(f"  ⚠️ Ошибка при проверке правила '{rule_name}': {e}")
            conn.rollback()
            errors += 1
    
    return errors == 0

def main():
    print("🚀 Запуск валидатора Data Contract...")
    
    # 1. Загружаем контракт
    contract = load_contract(CONTRACT_PATH)
    print(f"📄 Контракт загружен: {contract['dataset']['name']} (владелец: {contract['dataset']['owner']})")
    
    # 2. Подключаемся к БД
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    # 3. Проверяем колонки
    columns_ok = validate_columns(conn, contract)
    
    # 4. Проверяем правила качества
    rules_ok = validate_rules(conn, contract)
    
    conn.close()
    
    # 5. Итог
    print("\n" + "=" * 60)
    if columns_ok and rules_ok:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Данные соответствуют контракту.")
        sys.exit(0)
    else:
        print("❌ НАЙДЕНЫ НАРУШЕНИЯ КОНТРАКТА. Исправьте данные или обновите контракт.")
        sys.exit(1)

if __name__ == "__main__":
    main()
