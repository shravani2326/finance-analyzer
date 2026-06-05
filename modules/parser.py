import pandas as pd

def load_csv(file):
    if hasattr(file, 'name'):
        filename = file.name.lower()
    else:
        filename = str(file).lower()

    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        df = pd.read_excel(file)
    else:
        df = pd.read_csv(file, skipinitialspace=True)

    df.columns = df.columns.str.strip()
    df['Date']   = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    if 'Category' not in df.columns:
        df['Category'] = None

    if 'Type' not in df.columns:
        df['Type'] = df['Amount'].apply(
            lambda x: 'Credit' if x > 0 else 'Debit'
        )
    return df

def get_summary(df):
    income  = df[df['Amount'] > 0]['Amount'].sum()
    expense = df[df['Amount'] < 0]['Amount'].abs().sum()
    return {
        'total_income'       : round(income, 2),
        'total_expense'      : round(expense, 2),
        'net_savings'        : round(income - expense, 2),
        'total_transactions' : len(df)
    }