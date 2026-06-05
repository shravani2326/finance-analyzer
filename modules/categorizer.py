import mysql.connector
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "a.env")
def get_connection():
    return mysql.connector.connect(
        host     = "localhost",
        port     = 3306,
        user     = "root",
        password = "Shravani@23",
        database = "finance_analyzer"
    )

# ── Cell 20 ──
def get_category(description):
    conn   = get_connection()
    cursor = conn.cursor()
    description = description.upper().strip()
    cursor.execute("SELECT merchant_keyword, category FROM merchant_categories")
    merchants = cursor.fetchall()
    cursor.close()
    conn.close()
    for keyword, category in merchants:
        if keyword in description:
            return category
    return "Unknown"

# ── Cell 21 ──
def get_all_categories():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category_name FROM categories")
    result = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return result
# ── Cell 23 ──
def save_new_category(category_name):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT IGNORE INTO categories(category_name) VALUES(%s)",
        (category_name,)
    )
    conn.commit()
    cursor.close()
    conn.close()
def save_new_merchant(merchant, category):
    existing = get_all_categories()
    if category not in existing:
        save_new_category(category)
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT IGNORE INTO merchant_categories VALUES(%s,%s)",
        (merchant, category)
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ '{merchant}' → '{category}' saved!")