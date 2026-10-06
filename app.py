import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from apscheduler.schedulers.background import BackgroundScheduler

st.set_page_config(page_title="Furnace Charging System", layout="wide")

DATA_FILE = "heat_records.csv"
MATERIALS = ["MS", "CRC", "CI", "PIG", "SG BORING", "CI BORING", "SOLED", "R.R"]

# --- INDIAN TIMEZONE (IST) CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')

def get_current_ist():
    return datetime.now(IST)

# --- EMAIL CONFIGURATION ---
# Tumcha Gmail Ani App Password Ethhe Taka:
SENDER_EMAIL = "sanyogkamble55@gmail.com"        # Tumcha Gmail ID
SENDER_PASSWORD = "sanyogkamble0507"     # Google App Password (16-digit)
RECEIVER_EMAIL = "sanyogkamble55@gmail.com"      # Email milnyasathi cha Receiver ID

# Function: Gmail Pathawnyasathi Logic
def send_email_notification(subject, body_text, attach_csv=True):
    if not os.path.exists(DATA_FILE):
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body_text, 'plain'))

        if attach_csv:
            df = pd.read_csv(DATA_FILE)
            today_str = get_current_ist().strftime("%Y-%m-%d")
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            part = MIMEApplication(csv_bytes, Name=f"Furnace_Report_{today_str}.csv")
            part['Content-Disposition'] = f'attachment; filename="Furnace_Report_{today_str}.csv"'
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False

# Function: Automated 12-Hour Scheduled Report
def send_12hr_email_report():
    today_str = get_current_ist().strftime("%Y-%m-%d")
    subject = f"🔥 Furnace Charging 12-Hour Automated Report - {today_str}"
    body = f"Namaskar,\n\nAttached ahe aajcha Furnace Charging Automated Data Report ({today_str}).\n\nDhanyawad!"
    send_email_notification(subject, body, attach_csv=True)

# Background Scheduler (Every 12 Hours Trigger)
@st.cache_resource
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_12hr_email_report, 'interval', hours=12)
    scheduler.start()

start_scheduler()

# --- १. ऑपरेटर सेशन मॅनेजमेंट ---
if "operator_name" not in st.session_state:
    st.session_state["operator_name"] = ""

if "rows_count" not in st.session_state:
    st.session_state["rows_count"] = 1

st.markdown("<h2 style='text-align: center;'>🔥 Furnace Charging Entry System</h2>", unsafe_allow_html=True)

# ऑपरेटर लॉगिन स्क्रीन
if not st.session_state["operator_name"]:
    st.subheader("👤 Operator Login")
    with st.form("login_form"):
        op_name = st.text_input("Operator Name (ऑपरेटरचे नाव टाका)")
        login_btn = st.form_submit_button("Login")
        if login_btn:
            if op_name.strip():
                st.session_state["operator_name"] = op_name.strip()
                st.rerun()