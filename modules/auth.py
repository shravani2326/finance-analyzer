import mysql.connector
import hashlib
import re
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "a.env")

def get_connection():
    return mysql.connector.connect(
        host     = os.getenv("DB_HOST"),
        port     = int(os.getenv("DB_PORT", 3306)),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        database = os.getenv("DB_NAME")
    )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def register_user(username, email, password):
    # Validate inputs
    if len(username) < 3:
        return False, "❌ Username must be at least 3 characters!"
    if not is_valid_email(email):
        return False, "❌ Invalid email address!"
    if len(password) < 6:
        return False, "❌ Password must be at least 6 characters!"

    conn   = get_connection()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
        """, (username, email, password_hash))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "✅ Registration successful! Please login."
    except mysql.connector.IntegrityError:
        cursor.close()
        conn.close()
        return False, "❌ Username or email already exists!"

def login_user(username, password):
    conn   = get_connection()
    cursor = conn.cursor()

    password_hash = hash_password(password)
    cursor.execute("""
        SELECT id, username, email
        FROM users
        WHERE username=%s AND password_hash=%s
    """, (username, password_hash))

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return True, {
            "id"      : user[0],
            "username": user[1],
            "email"   : user[2]
        }
    return False, "❌ Invalid username or password!"

def get_user_by_id(user_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email FROM users WHERE id=%s",
        (user_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return {"id": user[0], "username": user[1], "email": user[2]}
    return None