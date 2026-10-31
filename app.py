from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import threading
import pandas as pd
import plotly.express as px
import pytz
import streamlit as st

st.set_page_config(page_title="Furnace Charging System", layout="wide")

DATA_FILE = "heat_records.csv"
MATERIALS = ["MS", "CRC", "CI", "PIG", "SG BORING", "CI BORING", "SOLED", "R.R"]

IST = pytz.timezone("Asia/Kolkata")


def get_current_ist():
    return datetime.now(IST)


def clean_and_fix_existing_csv():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if "Material" in df.columns:
                df["Material"] = df["Material"].str.strip().str.upper()
                replacements = {
                    "C.I BORING": "CI BORING",
                    "C.I. BORING": "CI BORING",
                    "S.G BORING": "SG BORING",
                    "S.G. BORING": "SG BORING",
                    "SOLID": "SOLED",
                    "C.I": "CI",
                    "C.I.": "CI",
                }
                df["Material"] = df["Material"].replace(replacements)
                df.to_csv(DATA_FILE, index=False)
        except Exception as e:
            print(f"Error cleaning CSV: {e}")


clean_and_fix_existing_csv()

SENDER_EMAIL = "swapnilchougule155@gmail.com"
SENDER_PASSWORD = "deac qbfg nmvi qsgc"
RECEIVER_EMAIL = "swapnilchougule155@gmail.com"


def _send_email_async(
    subject,
    body_text,
    file_to_attach=None,
    filename=None,
    image_bytes=None,
    img_filename="furnace_graph.png",
):
    try:
        clean_pwd = SENDER_PASSWORD.replace(" ", "")
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        if file_to_attach is not None and filename is not None:
            part = MIMEApplication(file_to_attach, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            msg.attach(part)
        elif os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            today_str = get_current_ist().strftime("%Y-%m-%d")
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            part = MIMEApplication(csv_bytes, Name=f"Furnace_Report_{today_str}.csv")
            part[
                "Content-Disposition"
            ] = f'attachment; filename="Furnace_Report_{today_str}.csv"'
            msg.attach(part)

        if image_bytes is not None:
            img_part = MIMEImage(image_bytes, name=img_filename)
            img_part["Content-Disposition"] = (
                f'attachment; filename="{img_filename}"'
            )
            msg.attach(img_part)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(SENDER_EMAIL, clean_pwd)
            server.send_message(msg)
    except Exception as e:
        print(f"Background Email Exception: {e}")


def send_email_notification_async(
    subject,
    body_text,
    file_to_attach=None,
    filename=None,
    image_bytes=None,
    img_filename="furnace_graph.png",
):
    thread = threading.Thread(
        target=_send_email_async,
        args=(
            subject,
            body_text,
            file_to_attach,
            filename,
            image_bytes,
            img_filename,
        ),
    )
    thread.daemon = True
    thread.start()


if "operator_name" not in st.session_state:
    st.session_state["operator_name"] = ""

st.markdown(
    "<h2 style='text-align: center;'>🔥 Furnace Charging Entry System</h2>",
    unsafe_allow_html=True,
)

if not st.session_state["operator_name"]:
    st.subheader("👤 Operator Login")
    with st.form("login_form"):
        op_name = st.text_input("Operator Name (ऑपरेटरचे नाव टाका)")
        login_btn = st.form_submit_button("Login")
        if login_btn:
            if op_name.strip():
                st.session_state["operator_name"] = op_name.strip()
                st.rerun()
            else:
                st.warning("कृपया ऑपरेटरचे नाव टाका!")
    st.stop()

col_op1, col_op2 = st.columns([4, 1])
with col_op1:
    st.success(f"**सक्रिय ऑपरेटर (Active Operator):** {st.session_state['operator_name']}")
with col_op2:
    if st.button("Logout", type="primary"):
        st.session_state["operator_name"] = ""
        st.rerun()

st.markdown("---")

with st.sidebar:
    st.subheader("🎯 Material Target Weights")
    default_targets = {
        "MS": 150.0,
        "CRC": 150.0,
        "CI": 150.0,
        "PIG": 150.0,
        "SG BORING": 150.0,
        "CI BORING": 150.0,
        "SOLED": 150.0,
        "R.R": 150.0,
    }
    target_weights = {}
    for mat in MATERIALS:
        target_weights[mat] = st.number_input(
            f"{mat} Target (Kg):",
            value=default_targets.get(mat, 150.0),
            step=1.0,
            key=f"target_{mat}",
        )

st.subheader("📝 Raw Material Weight Entry")
form_weights = {}

for mat in MATERIALS:
    col_label, col_input, col_status = st.columns([2, 2, 3])
    with col_label:
        st.markdown(f"**{mat}**")
    with col_input:
        wt_str = st.text_input(
            f"Weight for {mat}",
            value="",
            placeholder="वजन टाका (उदा. 150)",
            key=f"vert_wt_{mat}",
            label_visibility="collapsed",
        )
        form_weights[mat] = wt_str
    with col_status:
        target_val = target_weights.get(mat, 150.0)
        try:
            wt = float(wt_str) if wt_str.strip() else 0.0
        except ValueError:
            wt = 0.0

        if wt > 0:
            if wt == target_val:
                st.markdown(
                    f"<div style='background-color:#d4edda; color:#155724; padding:5px; border-radius:5px; text-align:center;'>🟢 अचूक ({wt} == {target_val})</div>",
                    unsafe_allow_html=True,
                )
            elif wt < target_val:
                st.markdown(
                    f"<div style='background-color:#fff3cd; color:#856404; padding:5px; border-radius:5px; text-align:center;'>🟡 कमी ({wt} < {target_val})</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background-color:#f8d7da; color:#721c24; padding:5px; border-radius:5px; text-align:center;'>🔴 जास्त ({wt} > {target_val})</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<div style='color:gray; padding:5px; text-align:center;'>वजन प्रविष्ट करा</div>",
                unsafe_allow_html=True,
            )

st.markdown("<br>", unsafe_allow_html=True)

if st.button(
    "Save Entry (सर्व नोंदी सेव्ह करा)", type="primary", use_container_width=True
):
    valid_entries = {}
    for m, w_str in form_weights.items():
        if w_str.strip():
            try:
                val = float(w_str)
                if val > 0:
                    valid_entries[m] = val
            except ValueError:
                pass

    if not valid_entries:
        st.warning("कृपया कमीत कमी एका मटेरियलचे वजन टाका!")
    else:
        now = get_current_ist()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        new_rows = []
        for mat, wt in valid_entries.items():
            new_rows.append({
                "Date": date_str,
                "Time": time_str,
                "Operator": st.session_state["operator_name"],
                "Material": mat,
                "Weight": wt,
            })

        df_new = pd.DataFrame(new_rows)

        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            df_existing = pd.read_csv(DATA_FILE)
            if "Heat No" in df_existing.columns:
                df_existing = df_existing.drop(columns=["Heat No"])
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        df_combined.to_csv(DATA_FILE, index=False)
        clean_and_fix_existing_csv()

        # Gather all entries for today to send in email body
        df_today = df_combined[df_combined["Date"] == date_str]
        today_summary_text = df_today.to_string(index=False)

        st.success("✅ Furnace Entry saved successfully!")
        subject = f"🚨 New Furnace Entries Saved for {date_str} ({st.session_state['operator_name']})"
        body = f"New Entry Saved by Operator: {st.session_state['operator_name']}\nTime: {time_str}\n\n--- ALL ENTRIES FOR TODAY ({date_str}) ---\n\n{today_summary_text}"
        
        send_email_notification_async(subject, body)
        st.rerun()

st.markdown("---")
st.subheader("🗓️ Date-wise Saved Report & Material Analysis")

if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
    try:
        df_all = pd.read_csv(DATA_FILE)
        clean_and_fix_existing_csv()
        df_all = pd.read_csv(DATA_FILE)

        if "Heat No" in df_all.columns:
            df_all = df_all.drop(columns=["Heat No"])

        df_all = df_all.dropna(subset=["Date"])
        df_all["Date_dt"] = pd.to_datetime(df_all["Date"], errors="coerce")
        df_all = df_all.dropna(subset=["Date_dt"])

        if not df_all.empty:
            df_all["Month_Year"] = df_all["Date_dt"].dt.strftime("%B %Y")
            all_months = df_all["Month_Year"].unique().tolist()

            selected_month = st.selectbox(
                "महिना निवडा (Select Month):", all_months
            )

            if selected_month:
                df_filtered = df_all[df_all["Month_Year"] == selected_month].copy()

                pivot_df = df_filtered.pivot_table(
                    index=["Date", "Time", "Operator"],
                    columns="Material",
                    values="Weight",
                    aggfunc="sum",
                    fill_value=0,
                ).reset_index()

                for m in MATERIALS:
                    if m not in pivot_df.columns:
                        pivot_df[m] = 0.0

                pivot_df["Total Weight"] = pivot_df[MATERIALS].sum(axis=1)

                # --- 📅 DATE-WISE SORTING (Latest entries on top) ---
                pivot_df = pivot_df.sort_values(by=["Date", "Time"], ascending=[False, False])

                final_cols = (
                    ["Date", "Time", "Operator"] + MATERIALS + ["Total Weight"]
                )
                pivot_df = pivot_df[final_cols]

                st.markdown("#### 📋 Date-wise Entry & Quantity Report")
                st.dataframe(pivot_df, use_container_width=True)

                # --- 📊 MATERIAL USAGE INSIGHTS (Highest, Lowest, Equal) ---
                st.markdown("#### 📊 Material Usage Analysis (Insights)")
                
                material_sums = {}
                for m in MATERIALS:
                    if m in pivot_df.columns:
                        material_sums[m] = pivot_df[m].sum()
                
                if material_sums:
                    max_mat = max(material_sums, key=material_sums.get)
                    min_mat = min(material_sums, key=material_sums.get)
                    
                    col_ins1, col_ins2, col_ins3 = st.columns(3)
                    with col_ins1:
                        st.info(f"📈 **Sarvat Jast Vaporlele (Highest):**\n\n**{max_mat}** ({material_sums[max_mat]:.2f} Kg)")
                    with col_ins2:
                        st.warning(f"📉 **Sarvat Kami Vaporlele (Lowest):**\n\n**{min_mat}** ({material_sums[min_mat]:.2f} Kg)")
                    with col_ins3:
                        target_summary = []
                        for m in MATERIALS:
                            t_val = target_weights.get(m, 150.0)
                            avg_v = pivot_df[m].mean() if m in pivot_df.columns else 0
                            if abs(avg_v - t_val) < 1e-5 and avg_v > 0:
                                target_summary.append(m)
                        match_str = ", ".join(target_summary) if target_summary else "Konihi Nahi"
                        st.success(f"🎯 **Target Pramane Saman/Achuk:**\n\n**{match_str}**")

                # --- 📈 GRAPHICAL ANALYTICS SECTION ---
                st.markdown(
                    "<h4 style='text-align: center;'>📈 Visual Analytics & Graphs</h4>",
                    unsafe_allow_html=True,
                )

                available_dates = sorted(pivot_df["Date"].unique().tolist(), reverse=True)
                selected_date_filter = st.selectbox(
                    "दिनांक फिल्टर निवडा (Select Date for Graph):",
                    ["सर्व तारखा (All Dates - Monthly View)"] + available_dates,
                )

                if (
                    selected_date_filter
                    != "सर्व तारखा (All Dates - Monthly View)"
                ):
                    df_graph_source = pivot_df[
                        pivot_df["Date"] == selected_date_filter
                    ]
                else:
                    df_graph_source = pivot_df

                chart_data = []
                for m in MATERIALS:
                    mat_wt = (
                        df_graph_source[m].sum()
                        if m in df_graph_source.columns
                        else 0.0
                    )
                    count_entries = (
                        (df_graph_source[m] > 0).sum()
                        if m in df_graph_source.columns
                        else 1
                    )
                    if count_entries == 0:
                        count_entries = 1
                    avg_wt = mat_wt / count_entries
                    target_val = target_weights.get(m, 150.0)

                    if avg_wt > target_val:
                        status = "🔴 जास्त (Red)"
                    elif avg_wt == target_val and avg_wt > 0:
                        status = "🟢 अचूक (Green)"
                    elif avg_wt < target_val and avg_wt > 0:
                        status = "🟡 कमी (Yellow)"
                    else:
                        status = "🟡 कमी (Yellow)"

                    chart_data.append({
                        "Material": m,
                        "Average Weight": avg_wt,
                        "Target Weight": target_val,
                        "Status": status,
                    })

                df_chart = pd.DataFrame(chart_data)
                df_chart["Status"] = pd.Categorical(
                    df_chart["Status"],
                    categories=[
                        "🟢 अचूक (Green)",
                        "🟡 कमी (Yellow)",
                        "🔴 जास्त (Red)",
                    ],
                    ordered=True,
                )

                fig = px.bar(
                    df_chart,
                    x="Material",
                    y="Average Weight",
                    color="Status",
                    color_discrete_map={
                        "🟢 अचूक (Green)": "#28a745",
                        "🟡 कमी (Yellow)": "#ffc107",
                        "🔴 जास्त (Red)": "#dc3545",
                    },
                    title="मटेरियलनुसार वजन स्टेटस ग्राफ (Color Status Graph)",
                )

                st.plotly_chart(fig, use_container_width=True)

                grand_total = df_graph_source["Total Weight"].sum()

                col_t1, col_t2 = st.columns([2, 2])
                with col_t1:
                    csv_data = df_graph_source.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Date-wise Report (CSV)",
                        data=csv_data,
                        file_name=(
                            "Furnace_DateWise_Report_"
                            f"{selected_month.replace(' ', '_')}.csv"
                        ),
                        mime="text/csv",
                    )
                with col_t2:
                    st.markdown(
                        f"<h4 style='text-align: right; color: #1E88E5;'>Grand Total: {grand_total:.2f} Kg</h4>",
                        unsafe_allow_html=True,
                    )
    except Exception as e:
        st.error(f"Error loading report: {e}")