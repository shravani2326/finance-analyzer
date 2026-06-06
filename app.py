import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules.parser      import load_csv, get_summary
from modules.categorizer import get_category, save_new_merchant, get_all_categories
from modules.insights    import generate_ai_recommendations, DISCRETIONARY_CATEGORIES, ESSENTIAL_CATEGORIES
from modules.monthly     import (create_tables, save_monthly_summary,
                                  get_previous_month, get_monthly_history,
                                  compare_months)
from modules.auth        import register_user, login_user

st.set_page_config(
    page_title = "Personal Finance Analyzer",
    page_icon  = "💰",
    layout     = "wide"
)

create_tables()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.logged_in:

    st.title("💰 Personal Finance Analyzer")
    st.markdown("Your personal AI-powered finance tracking system.")
    st.divider()

    auth_tab1, auth_tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with auth_tab1:
        st.subheader("🔐 Login to Your Account")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", use_container_width=True):
            if username and password:
                success, result = login_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user      = result
                    st.success(f"✅ Welcome back, {result['username']}!")
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.warning("⚠️ Please enter username and password!")

    with auth_tab2:
        st.subheader("📝 Create New Account")
        new_username = st.text_input("Username",         key="reg_user")
        new_email    = st.text_input("Email",            key="reg_email")
        new_password = st.text_input("Password",         type="password", key="reg_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Register", use_container_width=True):
            if new_username and new_email and new_password and confirm_pass:
                if new_password != confirm_pass:
                    st.error("❌ Passwords do not match!")
                else:
                    success, message = register_user(new_username, new_email, new_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            else:
                st.warning("⚠️ Please fill all fields!")

else:
    user_id  = st.session_state.user["id"]
    username = st.session_state.user["username"]

    col1, col2 = st.columns([8, 2])
    with col1:
        st.title("💰 Personal Finance Analyzer")
        st.markdown(f"Welcome, **{username}**! 👋")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user      = None
            st.rerun()

    st.divider()

    uploaded_file = st.file_uploader(
        "📂 Upload Bank Statement (CSV or Excel)",
        type=["csv", "xlsx", "xls"]
    )

    # ════════════════════════════════════════════
    # NO FILE UPLOADED
    # ════════════════════════════════════════════
    if not uploaded_file:

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Dashboard",
            "🤖 AI Recommendations",
            "📅 Comparison",
            "📋 History"
        ])

        with tab1:
            st.info("📂 Upload a bank statement to see your dashboard.")
        with tab2:
            st.info("📂 Upload a bank statement to get AI recommendations.")
        with tab3:
            st.info("📂 Upload a file to see month vs month comparison.")

        with tab4:
            st.subheader("📋 Monthly History")
            history = get_monthly_history(user_id)

            if len(history) == 0:
                st.info("No history found. Upload your first month to get started.")
            else:
                history["Status"] = history["Net_Savings"].apply(
                    lambda x: "✅ Positive" if x >= 0 else "❌ Negative"
                )
                history_display = history.drop(columns=["Month"]).rename(columns={
                    "Month_Year" : "Month",
                    "Income"     : "Income (₹)",
                    "Expense"    : "Expense (₹)",
                    "Net_Savings": "Net Savings (₹)"
                })
                st.dataframe(history_display, use_container_width=True)
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📈 Savings Trend")
                    fig_sav = px.line(
                        history, x="Month_Year", y="Net_Savings",
                        markers=True, color_discrete_sequence=["green"]
                    )
                    fig_sav.add_hline(y=0, line_dash="dash", line_color="red")
                    st.plotly_chart(fig_sav, use_container_width=True)

                with col2:
                    st.subheader("📊 Income vs Expense Trend")
                    fig_trend = px.bar(
                        history, x="Month_Year",
                        y=["Income", "Expense"],
                        barmode="group",
                        color_discrete_map={"Income": "green", "Expense": "red"}
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

    # ════════════════════════════════════════════
    # FILE UPLOADED
    # ════════════════════════════════════════════
    else:
        df = load_csv(uploaded_file)
        df["Category"] = df["Description"].apply(get_category)

        # ── Unknown Merchants ─────────────────────
        unknown = df[df["Category"] == "Unknown"]["Description"].unique()

        if len(unknown) > 0:
            st.warning(f"⚠️ {len(unknown)} unknown merchants found! Please categorize them:")

            with st.form("unknown_merchants_form"):
                all_cats       = get_all_categories()
                new_entries    = {}
                new_cat_inputs = {}

                for merchant in unknown:
                    st.markdown(f"### 🏪 {merchant}")
                    col1, col2 = st.columns([2, 2])
                    with col1:
                        selected = st.selectbox(
                            "Select Category",
                            options = all_cats + ["➕ Add New Category"],
                            key     = f"select_{merchant}"
                        )
                        new_entries[merchant] = selected
                    with col2:
                        new_cat = st.text_input(
                            "New Category Name (if adding new)",
                            key         = f"newcat_{merchant}",
                            placeholder = "e.g. Hobby, Sports, Pet Care"
                        )
                        new_cat_inputs[merchant] = new_cat
                    st.divider()

                submitted = st.form_submit_button("✅ Save All Categories", use_container_width=True)

                if submitted:
                    all_saved = True
                    for merchant in unknown:
                        category     = new_entries.get(merchant, "")
                        new_cat_name = new_cat_inputs.get(merchant, "").strip()

                        if category == "➕ Add New Category":
                            if new_cat_name:
                                save_new_category(new_cat_name)
                                save_new_merchant(merchant.upper().strip(), new_cat_name)
                                st.success(f"✅ '{merchant}' → '{new_cat_name}' saved!")
                            else:
                                st.error(f"❌ Please enter a category name for: {merchant}")
                                all_saved = False
                        else:
                            save_new_merchant(merchant.upper().strip(), category)
                            st.success(f"✅ '{merchant}' → '{category}' saved!")

                    if all_saved:
                        st.success("✅ All categories saved! Reloading...")
                        st.rerun()

            

        # ── Month Confirmation ────────────────────
        save_key = f"saved_{uploaded_file.name}_{user_id}"

        if save_key not in st.session_state:
            st.divider()
            with st.container(border=True):
                st.markdown("### 📅 Confirm Month for this Statement")
                col1, col2 = st.columns([3, 1])
                with col1:
                    auto_month = pd.to_datetime(df["Date"]).max().strftime("%b-%Y")
                    month_year = st.text_input(
                        "Enter Month (e.g. Jan-2024, Feb-2025)",
                        value = auto_month
                    )
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("✅ Confirm & Analyze", use_container_width=True):
                        save_monthly_summary(df, month_year, user_id)
                        st.session_state[save_key] = month_year
                        # Clear any cached AI results for fresh analysis
                        ai_cache_key = f"ai_{user_id}_{month_year}"
                        if ai_cache_key in st.session_state:
                            del st.session_state[ai_cache_key]
                        st.rerun()

            st.stop()

        # ── Confirmed — Show Full App ─────────────
        else:
            month_year = st.session_state[save_key]

            # ── Expenses & Budget DataFrame ───────
            expenses     = df[df["Type"] == "Debit"]
            cat_spending = expenses.groupby("Category")["Amount"].sum().abs()
            budget_df    = cat_spending.reset_index()
            budget_df.columns = ["Category", "Spent"]

            all_expense_cats   = budget_df["Category"].tolist()
            budget_session_key = f"budget_{user_id}_{month_year}"

            if budget_session_key not in st.session_state:
                st.session_state[budget_session_key] = {
                    cat: 0 for cat in all_expense_cats
                }
            else:
                for cat in all_expense_cats:
                    if cat not in st.session_state[budget_session_key]:
                        st.session_state[budget_session_key][cat] = 0

            # ── Budget Form ───────────────────────
            with st.expander("⚙️ Set Your Monthly Budget", expanded=False):
                st.markdown("Type your budget for each category and click **Save Budget**:")

                with st.form("budget_form"):
                    cols        = st.columns(3)
                    temp_budget = {}

                    for i, cat in enumerate(all_expense_cats):
                        with cols[i % 3]:
                            temp_budget[cat] = st.text_input(
                                f"{cat} (₹)",
                                value = str(int(st.session_state[budget_session_key].get(cat, 0))),
                                key   = f"budget_{cat}_{month_year}"
                            )

                    if st.form_submit_button("💾 Save Budget", use_container_width=True):
                        converted_budget = {}
                        for cat, val in temp_budget.items():
                            try:
                                converted_budget[cat] = int(val)
                            except:
                                converted_budget[cat] = 0
                        st.session_state[budget_session_key] = converted_budget

                        # Clear AI cache so it regenerates with new budget
                        ai_cache_key = f"ai_{user_id}_{month_year}"
                        if ai_cache_key in st.session_state:
                            del st.session_state[ai_cache_key]
                        st.success("✅ Budget saved!")
                        st.rerun()

            user_budget = st.session_state[budget_session_key]

            # ── Budget DataFrame ──────────────────
            budget_df["Budget"]     = budget_df["Category"].map(user_budget).fillna(0)
            budget_df["Difference"] = budget_df["Spent"] - budget_df["Budget"]
            budget_df["Status"]     = budget_df["Difference"].apply(
                lambda x: "🔴 Over Budget" if x > 0 else "🟢 Within Budget"
            )

            summary = get_summary(df)

            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Dashboard",
                "🤖 AI Recommendations",
                "📅 Comparison",
                "📋 History"
            ])

            # ── TAB 1 DASHBOARD ───────────────────
            with tab1:
                st.subheader("📊 Monthly Overview")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("💵 Total Income",   f"₹{summary['total_income']:,.0f}")
                col2.metric("💸 Total Expenses", f"₹{summary['total_expense']:,.0f}")
                col3.metric("🏦 Net Savings",    f"₹{summary['net_savings']:,.0f}")
                col4.metric("🧾 Transactions",   summary['total_transactions'])
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🥧 Spending by Category")
                    fig_pie = px.pie(
                        budget_df, names="Category", values="Spent", hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col2:
                    st.subheader("📊 Budget vs Actual")
                    budget_chart = budget_df[budget_df["Budget"] > 0]
                    if len(budget_chart) > 0:
                        fig_bar = go.Figure()
                        fig_bar.add_trace(go.Bar(
                            name="Budget", x=budget_chart["Category"],
                            y=budget_chart["Budget"], marker_color="lightblue"
                        ))
                        fig_bar.add_trace(go.Bar(
                            name="Spent", x=budget_chart["Category"],
                            y=budget_chart["Spent"],
                            marker_color=budget_chart["Status"].apply(
                                lambda x: "red" if x == "🔴 Over Budget" else "green"
                            )
                        ))
                        fig_bar.update_layout(barmode="group")
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info("⚙️ Set your budget above to see Budget vs Actual chart.")

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📈 Daily Spending Trend")
                    daily         = expenses.copy()
                    daily["Date"] = pd.to_datetime(daily["Date"])
                    daily_spend   = daily.groupby("Date")["Amount"].sum().abs().reset_index()
                    fig_line      = px.line(daily_spend, x="Date", y="Amount", markers=True)
                    st.plotly_chart(fig_line, use_container_width=True)

                with col2:
                    st.subheader("🏆 Top 10 Expenses")
                    top10           = expenses.nlargest(10, "Amount")[["Description","Amount"]].copy()
                    top10["Amount"] = top10["Amount"].abs()
                    fig_top         = px.bar(top10, x="Amount", y="Description", orientation="h")
                    fig_top.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_top, use_container_width=True)

                st.subheader("📄 All Transactions")
                st.dataframe(
                    df[["Date","Description","Amount","Category","Type"]],
                    use_container_width=True
                )

            # ── TAB 2 AI RECOMMENDATIONS ──────────
            with tab2:
                st.subheader("🤖 AI-Powered Savings Recommendations")

                ai_cache_key = f"ai_{user_id}_{month_year}"

                if ai_cache_key not in st.session_state:
                    with st.spinner("🤖 Analyzing your spending with AI..."):
                        st.session_state[ai_cache_key] = generate_ai_recommendations(budget_df, df)

                results = st.session_state[ai_cache_key]

                st.markdown("### 📊 Where You Can Save")
                for item in results["discretionary"]:
                    if item["status"] == "🔴 Over Budget":
                        with st.container(border=True):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Category", item["category"])
                            col2.metric("Spent",    f"₹{item['spent']:,.0f}")
                            col3.metric("Over By",  f"₹{item['diff']:,.0f}", delta_color="inverse")
                            if item["tip"]:
                                st.info(f"💡 {item['tip']}")
                    else:
                        with st.container(border=True):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Category", item["category"])
                            col2.metric("Spent",    f"₹{item['spent']:,.0f}")
                            col3.metric("Saved",    f"₹{abs(item['diff']):,.0f}")
                            st.success(f"✅ Within budget for {item['category']}!")

                st.divider()
                st.markdown("### 📌 Essential Expenses — No Changes Recommended")
                if len(results["essential"]) > 0:
                    cols = st.columns(len(results["essential"]))
                    for i, item in enumerate(results["essential"]):
                        with cols[i]:
                            icon = "⚠️" if item["status"] == "🔴 Over Budget" else "✅"
                            st.metric(
                                f"{icon} {item['category']}",
                                f"₹{item['spent']:,.0f}",
                                f"₹{abs(item['diff']):,.0f} {'over' if item['diff'] > 0 else 'saved'}"
                            )

                st.divider()
                col1, col2 = st.columns(2)
                col1.metric("💸 Total Overspent",          f"₹{results['total_overspent']:,.0f}")
                col2.metric("💰 Potential Monthly Saving",  f"₹{results['total_overspent'] * 0.3:,.0f}")

            # ── TAB 3 COMPARISON ──────────────────
            with tab3:
                st.subheader("📅 Month vs Month Comparison")
                prev_month = get_previous_month(month_year, user_id)

                if prev_month is None:
                    st.info("⚠️ No previous month data found for comparison.")
                    st.write("ℹ️ Make sure you have uploaded and confirmed at least 2 months of data.")
                    st.write("📌 Go to History tab to see all uploaded months.")
                else:
                    st.success(f"Comparing **{month_year}** vs **{prev_month}**")
                    comp_df = compare_months(month_year, prev_month, user_id)

                    def color_trend(val):
                        if "▲" in str(val): return "color: red"
                        elif "▼" in str(val): return "color: green"
                        return ""

                    st.dataframe(
                        comp_df.style.map(color_trend, subset=["Trend"]),
                        use_container_width=True
                    )
                    fig_comp = px.bar(
                        comp_df, x="Category",
                        y=["Previous Month", "Current Month"],
                        barmode="group",
                        color_discrete_map={
                            "Previous Month": "lightblue",
                            "Current Month" : "coral"
                        }
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

            # ── TAB 4 HISTORY ─────────────────────
            with tab4:
                st.subheader("📋 Monthly History")
                history = get_monthly_history(user_id)

                if len(history) == 0:
                    st.info("No history found. Upload your first month to get started.")
                else:
                    history["Status"] = history["Net_Savings"].apply(
                        lambda x: "✅ Positive" if x >= 0 else "❌ Negative"
                    )
                    history_display = history.drop(columns=["Month"]).rename(columns={
                        "Month_Year" : "Month",
                        "Income"     : "Income (₹)",
                        "Expense"    : "Expense (₹)",
                        "Net_Savings": "Net Savings (₹)"
                    })
                    st.dataframe(history_display, use_container_width=True)
                    st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📈 Savings Trend")
                        fig_sav = px.line(
                            history, x="Month_Year", y="Net_Savings",
                            markers=True, color_discrete_sequence=["green"]
                        )
                        fig_sav.add_hline(y=0, line_dash="dash", line_color="red")
                        st.plotly_chart(fig_sav, use_container_width=True)

                    with col2:
                        st.subheader("📊 Income vs Expense Trend")
                        fig_trend = px.bar(
                            history, x="Month_Year",
                            y=["Income", "Expense"],
                            barmode="group",
                            color_discrete_map={"Income": "green", "Expense": "red"}
                        )
                        st.plotly_chart(fig_trend, use_container_width=True)