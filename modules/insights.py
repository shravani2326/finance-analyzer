from groq import Groq
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "a.env")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Cell 38 ──
DISCRETIONARY_CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping",
    "Entertainment", "Subscription", "Personal Care", "Fitness"
]

ESSENTIAL_CATEGORIES = [
    "Housing", "Healthcare", "Investment", "Education", "Utilities"
]

# ── Cell 40 ──
def get_ai_recommendation(category, spent, budget, df):
    cat_df = df[
        (df["Category"] == category) &
        (df["Type"] == "Debit")
    ][["Description", "Amount"]].copy()
    cat_df["Amount"] = cat_df["Amount"].abs()

    top_merchants = (
        cat_df.groupby("Description")["Amount"]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
        .head(5)
        .reset_index()
    )
    top_merchants.columns = ["Merchant", "Total_Spent", "Times"]
    budget    = budget if budget and budget > 0 else 0
    overspent = round(spent - budget, 2)
    is_over   = overspent > 0

    prompt = f"""
You are a friendly personal finance advisor for an Indian user.
Category      : {category}
Monthly Budget: Rs.{budget:,}
Actual Spent  : Rs.{spent:,}
{"Overspent By  : Rs." + str(overspent) + " WARNING" if is_over else "Under Budget By: Rs." + str(abs(overspent)) + " GOOD"}
Top merchants:
{top_merchants.to_string(index=False)}
Instructions:
- Give exactly 2-3 lines of advice
- Mention specific merchant names from the data above
- Give a realistic saving amount in Rs.
- Be friendly, specific and practical
- If within budget appreciate and give tip
- If over budget give one clear actionable suggestion
- Use Indian context
- Do NOT give generic advice
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


def generate_ai_recommendations(budget_df, df):
    results = {
        "discretionary" : [],
        "essential"     : [],
        "total_overspent": 0
    }

    for _, row in budget_df.iterrows():
        category = row["Category"]
        spent    = float(row["Spent"])
        budget   = float(row["Budget"])
        diff     = float(row["Difference"])
        status   = row["Status"]

        if category in ESSENTIAL_CATEGORIES:
            results["essential"].append({
                "category" : category,
                "spent"    : spent,
                "budget"   : budget,
                "diff"     : diff,
                "status"   : status
            })
        else:
            tip = get_ai_recommendation(
                category, spent, budget, df
            ) if status == "🔴 Over Budget" else None

            if status == "🔴 Over Budget":
                results["total_overspent"] += diff

            results["discretionary"].append({
                "category" : category,
                "spent"    : spent,
                "budget"   : budget,
                "diff"     : diff,
                "status"   : status,
                "tip"      : tip
            })

    return results