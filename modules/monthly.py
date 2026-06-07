import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv
from pathlib import Path
# Load .env from parent folder (finance_analyzer/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "a.env")

def get_month_order(month_year):
    try:
        return int(pd.to_datetime(month_year, format="%b-%Y").strftime("%Y%m"))
    except:
        return 0
def get_connection():
    return mysql.connector.connect(
       host     = os.getenv("DB_HOST"),
        port     = int(os.getenv("DB_PORT", 3306)),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        database = os.getenv("DB_NAME")
    )

def create_tables():
    conn   = get_connection()
    cursor = conn.cursor()

    # monthly_summary — added user_id column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_summary (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            month_year    VARCHAR(10),
            month_name    VARCHAR(20),
            total_income  FLOAT,
            total_expense FLOAT,
            net_savings   FLOAT,
            month_order   INT DEFAULT 0,
            user_id       INT DEFAULT NULL,
            upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_month (month_year, user_id)
        )
    """)

    # monthly_category_spending — added user_id column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_category_spending (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            month_year  VARCHAR(10),
            category    VARCHAR(50),
            amount      FLOAT,
            user_id     INT DEFAULT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tables ready!")


def save_monthly_summary(df, month_year, user_id):
    conn   = get_connection()
    cursor = conn.cursor()

    total_income  = df[df["Amount"] > 0]["Amount"].sum()
    total_expense = df[df["Amount"] < 0]["Amount"].abs().sum()
    net_savings   = total_income - total_expense
    month_name    = pd.to_datetime(df["Date"].iloc[0]).strftime("%B")
    order         = get_month_order(month_year)

    # Delete existing record for this user and month
    cursor.execute(
        "DELETE FROM monthly_summary WHERE month_year=%s AND user_id=%s",
        (month_year, user_id)
    )
    cursor.execute(
        "DELETE FROM monthly_category_spending WHERE month_year=%s AND user_id=%s",
        (month_year, user_id)
    )

    # Insert new summary
    cursor.execute("""
        INSERT INTO monthly_summary
        (month_year, month_name, total_income,
         total_expense, net_savings, month_order, user_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (month_year, month_name,
          float(total_income), float(total_expense),
          float(net_savings), order, user_id))

    # Insert category wise spending
    expenses     = df[df["Type"] == "Debit"]
    cat_spending = expenses.groupby("Category")["Amount"].sum().abs()
    for category, amount in cat_spending.items():
        cursor.execute("""
            INSERT INTO monthly_category_spending
            (month_year, category, amount, user_id)
            VALUES (%s,%s,%s,%s)
        """, (month_year, category, float(amount), user_id))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ {month_year} saved for user {user_id}!")


def get_previous_month(current_month_year, user_id):
    try:
        # Calculate previous month from calendar, not upload order
        current_date  = pd.to_datetime(current_month_year, format="%b-%Y")
        # Go back 1 month
        if current_date.month == 1:
            prev_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            prev_date = current_date.replace(month=current_date.month - 1)

        prev_month_year = prev_date.strftime("%b-%Y")

        # Check if that month exists in DB for this user
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT month_year FROM monthly_summary
            WHERE month_year = %s AND user_id = %s
        """, (prev_month_year, user_id))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return prev_month_year if result else None

    except Exception as e:
        print(f"Error getting previous month: {e}")
        return None


def get_monthly_history(user_id):
    conn   = get_connection()
    cursor = conn.cursor()

    # Get only THIS user's history
    cursor.execute("""
        SELECT month_year, month_name, total_income,
               total_expense, net_savings
        FROM monthly_summary
        WHERE user_id = %s
        ORDER BY month_order ASC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return pd.DataFrame(rows, columns=[
        "Month_Year", "Month",
        "Income", "Expense", "Net_Savings"
    ])


def compare_months(current_month, previous_month, user_id):
    conn   = get_connection()
    cursor = conn.cursor()

    # Get current month data for THIS user
    cursor.execute("""
        SELECT category, amount
        FROM monthly_category_spending
        WHERE month_year=%s AND user_id=%s
    """, (current_month, user_id))
    current = dict(cursor.fetchall())

    # Get previous month data for THIS user
    cursor.execute("""
        SELECT category, amount
        FROM monthly_category_spending
        WHERE month_year=%s AND user_id=%s
    """, (previous_month, user_id))
    previous = dict(cursor.fetchall())

    cursor.close()
    conn.close()

    all_categories = set(
        list(current.keys()) + list(previous.keys())
    )

    comparison = []
    for cat in all_categories:
        curr_amt   = current.get(cat, 0)
        prev_amt   = previous.get(cat, 0)
        change     = curr_amt - prev_amt
        change_pct = round(
            (change / prev_amt) * 100, 1
        ) if prev_amt > 0 else 100.0

        comparison.append({
            "Category"       : cat,
            "Previous Month" : round(prev_amt, 2),
            "Current Month"  : round(curr_amt, 2),
            "Change (Rs.)"   : round(change, 2),
            "Change (%)"     : change_pct,
            "Trend"          : "▲ More"  if change > 0
                               else "▼ Less" if change < 0
                               else "→ Same"
        })

    return pd.DataFrame(comparison).sort_values(
        "Change (Rs.)", ascending=False
    ).reset_index(drop=True)
