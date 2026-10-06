import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

st.set_page_config(page_title="Furnace Charging System", layout="wide")

DATA_FILE = "heat_records.csv"
MATERIALS = ["MS", "CRC", "CI", "PIG", "SG BORING", "CI BORING", "SOLED", "R.R"]

# --- INDIAN TIMEZONE (IST) ---
IST = pytz.timezone('Asia/Kolkata')

def get_current_ist():
    return datetime.now(IST)

# --- EMAIL CONFIGURATION ---
SENDER_EMAIL = "sanyogkamble55@gmail.com"
# NOTE: Ith 16-digit Google App Password taka (e.g., "abcd efgh ijkl mnop")
SENDER_PASSWORD = "sanyogkamble@0507"
RECEIVER_EMAIL = "sanyogkamble55@gmail.com"

def _send_email_async(subject, body_text):
    """Background thread to prevent UI freezing/hanging during email sending"""
    try:
        clean_pwd = SENDER_PASSWORD.replace(" ", "")
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))

        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            today_str = get_current_ist().strftime("%Y-%m-%d")
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            part = MIMEApplication(csv_bytes, Name=f"Furnace_Report_{today_str}.csv")
            part['Content-Disposition'] = f'attachment; filename="Furnace_Report_{today_str}.csv"'
            msg.attach(part)

        # Port 465 SSL connection
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
        server.login(SENDER_EMAIL, clean_pwd)
        server.send_message(msg)
        server.quit()
        print("Email Sent Successfully")
    except Exception as e:
        print(f"Background Email Exception: {e}")

def send_email_notification_async(subject, body_text):
    """Triggers background thread so save operation never gets blocked"""
    thread = threading.Thread(target=_send_email_async, args=(subject, body_text))
    thread.daemon = True
    thread.start()

# --- 1. SESSION MANAGEMENT ---
if "operator_name" not in st.session_state:
    st.session_state["operator_name"] = ""

if "rows_count" not in st.session_state:
    st.session_state["rows_count"] = 1

st.markdown("<h2 style='text-align: center;'>🔥 Furnace Charging Entry System</h2>", unsafe_allow_html=True)

# --- 2. OPERATOR LOGIN ---
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

# --- OPERATOR BANNER ---
col_op1, col_op2 = st.columns([4, 1])
with col_op1:
    st.success(f"**सक्रिय ऑपरेटर (Active Operator):** {st.session_state['operator_name']}")
with col_op2:
    if st.button("Logout", type="primary"):
        st.session_state["operator_name"] = ""
        st.rerun()

# --- 3. AUTO HEAT NO LOGIC (IST) ---
def get_next_heat_no():
    if not os.path.exists(DATA_FILE):
        return 1
    try:
        df = pd.read_csv(DATA_FILE)
        if df.empty or "Date" not in df.columns or "Heat No" not in df.columns:
            return 1
        
        today_str = get_current_ist().strftime("%Y-%m-%d")
        df_today = df[df["Date"] == today_str]
        
        if df_today.empty:
            return 1
        else:
            max_heat = df_today["Heat No"].max()
            return int(max_heat) + 1
    except Exception:
        return 1

suggested_heat_no = get_next_heat_no()

st.markdown("---")

# --- 4. CHARGING ENTRY FORM ---
col_h1, col_h2 = st.columns([2, 2])
with col_h1:
    current_heat_no = st.number_input(
        "Heat No (आजचा ऑटोमॅटिक पुढील हिट नंबर):", 
        value=suggested_heat_no, 
        min_value=1, 
        step=1
    )

st.write("**Materials & Weight (मटेरियल्स आणि वजन जोडा):**")

selected_entries = []
for i in range(st.session_state["rows_count"]):
    col_m, col_w = st.columns([2, 2])
    with col_m:
        mat = st.selectbox(
            f"Material #{i+1}", 
            ["-- Select Material --"] + MATERIALS, 
            key=f"mat_{i}",
            label_visibility="collapsed"
        )
    with col_w:
        wt = st.number_input(
            f"Weight #{i+1}", 
            min_value=0.0, 
            step=1.0, 
            value=None, 
            key=f"wt_{i}", 
            placeholder="Weight (Kg/Ton)",
            label_visibility="collapsed"
        )
    
    if mat != "-- Select Material --" and wt is not None and wt > 0:
        selected_entries.append((mat, wt))

col_b1, col_b2 = st.columns([2, 3])
with col_b1:
    if st.button("+ आणखी मटेरियल जोडा (Same Heat)"):
        st.session_state["rows_count"] += 1
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Save Heat Entry (हिट सेव्ह करा)", type="primary", use_container_width=True):
    if not selected_entries:
        st.warning("कृपया कमीत कमी एका Material चे