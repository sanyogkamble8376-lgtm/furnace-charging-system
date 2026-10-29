from datetime import datetime, timedelta
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

# --- INDIAN TIMEZONE (IST) ---
IST = pytz.timezone("Asia/Kolkata")


def get_current_ist():
  return datetime.now(IST)


# --- EMAIL CONFIGURATION ---
SENDER_EMAIL = "swapnilchougule155@gmail.com"
SENDER_PASSWORD = "oajf cgcx wrpx dsues"
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
    elif os.path.exists(DATA_FILE) and file_to_attach is None:
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


# --- 1. SESSION MANAGEMENT & 12-HOUR LOGIC ---
if "operator_name" not in st.session_state:
  st.session_state["operator_name"] = ""

if "login_time" not in st.session_state:
  st.session_state["login_time"] = None

if "rows_count" not in st.session_state:
  st.session_state["rows_count"] = 1

st.markdown(
    "<h2 style='text-align: center;'>🔥 Furnace Charging Entry System</h2>",
    unsafe_allow_html=True,
)

# --- 2. OPERATOR LOGIN ---
if not st.session_state["operator_name"]:
  st.subheader("👤 Operator Login")
  with st.form("login_form"):
    op_name = st.text_input("Operator Name (ऑपरेटरचे नाव टाका)")
    login_btn = st.form_submit_button("Login")
    if login_btn:
      if op_name.strip():
        clean_name = op_name.strip()
        st.session_state["operator_name"] = clean_name
        st.session_state["login_time"] = get_current_ist()
        st.rerun()
      else:
        st.warning("कृपया ऑपरेटरचे नाव टाका!")
  st.stop()

# --- OPERATOR BANNER ---
col_op1, col_op2 = st.columns([4, 1])
with col_op1:
  st.success(
      f"**सक्रिय ऑपरेटर (Active Operator):**"
      f" {st.session_state['operator_name']}"
  )
with col_op2:
  if st.button("Logout", type="primary"):
    st.session_state["operator_name"] = ""
    st.session_state["login_time"] = None
    st.rerun()


# --- 3. HEAT NO LOGIC WITH 12-HOUR CHECK ---
def get_next_heat_no(operator_name):
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

    if st.session_state["login_time"]:
      time_diff = get_current_ist() - st.session_state["login_time"]
      if time_diff <= timedelta(hours=12):
        df_op_today = df_today[df_today["Operator"] == operator_name]
        if not df_op_today.empty:
          return int(df_op_today["Heat No"].max())

    max_heat = df_today["Heat No"].max()
    return int(max_heat) + 1
  except Exception:
    return 1


suggested_heat_no = get_next_heat_no(st.session_state["operator_name"])

st.markdown("---")

# --- DAILY SUMMARY METRICS ---
if os.path.exists(DATA_FILE):
  try:
    df_summary = pd.read_csv(DATA_FILE)
    today_str = get_current_ist().strftime("%Y-%m-%d")
    if not df_summary.empty and "Date" in df_summary.columns:
      df_today_sum = df_summary[df_summary["Date"] == today_str]
      total_heats_today = (
          df_today_sum["Heat No"].nunique() if not df_today_sum.empty else 0
      )
      total_wt_today = (
          df_today_sum["Weight"].sum()
          if not df_today_sum.empty and "Weight" in df_summary.columns
          else 0.0
      )

      c_m1, c_m2 = st.columns(2)
      c_m1.metric(
          "📊 आज झालेली एकूण हिट्स (Total Heats Today)", f"{total_heats_today}"
      )
      c_m2.metric(
          "⚖️ आजचे एकूण चार्जिंग वजन (Total Weight Today)",
          f"{total_wt_today:.2f} Kg/Ton",
      )
  except Exception:
    pass

st.markdown("---")

# --- 4. TARGET WEIGHT SETTINGS IN SIDEBAR ---
with st.sidebar:
  st.subheader("🎯 Material Target Weights")
  st.write("प्रत्येक मटेरियलचे ठरलेले वजन सेट करा:")

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

# --- 5. CHARGING ENTRY FORM ---
col_h1, col_h2 = st.columns([2, 2])
with col_h1:
  current_heat_no = st.number_input(
      "Heat No (आजचा ऑटोमॅटिक हिट नंबर):",
      value=suggested_heat_no,
      min_value=1,
      step=1,
  )

st.write("**Materials & Weight (मटेरियल्स आणि वजन जोडा):**")

selected_entries = []
for i in range(st.session_state["rows_count"]):
  col_m, col_w, col_status = st.columns([2, 2, 2])
  with col_m:
    mat = st.selectbox(
        f"Material #{i+1}",
        ["-- Select Material --"] + MATERIALS,
        key=f"mat_{i}",
        label_visibility="collapsed",
    )
  with col_w:
    wt = st.number_input(
        f"Weight #{i+1}",
        min_value=0.0,
        step=1.0,
        value=None,
        key=f"wt_{i}",
        placeholder="Weight (Kg)",
        label_visibility="collapsed",
    )
  with col_status:
    if mat != "-- Select Material --" and wt is not None and wt > 0:
      target_val = target_weights.get(mat, 150.0)
      if wt == target_val:
        st.markdown(
            f"<div style='background-color: #d4edda; color: #155724; padding:"
            f" 8px; border-radius: 5px; text-align: center; font-weight:"
            f" bold;'>🟢 अचूक वजन ({wt} == {target_val})</div>",
            unsafe_allow_html=True,
        )
      elif wt < target_val:
        st.markdown(
            f"<div style='background-color: #fff3cd; color: #856404; padding:"
            f" 8px; border-radius: 5px; text-align: center; font-weight:"
            f" bold;'>🟡 वजन कमी आहे ({wt} < {target_val})</div>",
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            f"<div style='background-color: #f8d7da; color: #721c24; padding:"
            f" 8px; border-radius: 5px; text-align: center; font-weight:"
            f" bold;'>🔴 वजन जास्त आहे ({wt} > {target_val})</div>",
            unsafe_allow_html=True,
        )
    else:
      st.markdown(
          "<div style='color: gray; padding: 8px; text-align:"
          " center;'>वजन प्रविष्ट करा</div>",
          unsafe_allow_html=True,
      )

  if mat != "-- Select Material --" and wt is not None and wt > 0:
    selected_entries.append((mat, wt))

col_b1, col_b2 = st.columns([2, 3])
with col_b1:
  if st.button("+ आणखी मटेरियल जोडा (Same Heat)"):
    st.session_state["rows_count"] += 1
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

if st.button(
    "Save Heat Entry (हिट सेव्ह करा)", type="primary", use_container_width=True
):
  if not selected_entries:
    st.warning("Please select at least one Material and Weight!")
  else:
    now = get_current_ist()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    new_rows = []
    for mat, wt in selected_entries:
      new_rows.append({
          "Date": date_str,
          "Time": time_str,
          "Heat No": int(current_heat_no),
          "Operator": st.session_state["operator_name"],
          "Material": mat,
          "Weight": wt,
      })

    df_new = pd.DataFrame(new_rows)

    if os.path.exists(DATA_FILE):
      df_existing = pd.read_csv(DATA_FILE)
      if "Date/Time" in df_existing.columns:
        df_existing = df_existing.drop(columns=["Date/Time"])
      df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
      df_combined = df_new

    df_combined.to_csv(DATA_FILE, index=False)
    st.session_state["rows_count"] = 1
    st.success(f"✅ Heat No {int(current_heat_no)} saved successfully!")

    subject = (
        f"🚨 New Heat Entry: Heat No {int(current_heat_no)}"
        f" ({st.session_state['operator_name']})"
    )
    body = (
        f"New Heat Entry Saved:\n\nDate: {date_str}\nTime: {time_str}\nHeat No:"
        f" {int(current_heat_no)}\nOperator:"
        f" {st.session_state['operator_name']}"
    )
    send_email_notification_async(subject, body)

    st.rerun()

# --- SIDEBAR EMAIL CONTROLS ---
with st.sidebar:
  st.markdown("---")
  st.subheader("📧 Email Controls")
  st.info("Email notifications run automatically in the background.")

  st.markdown("---")
  st.write("**Manual Monthly Email Report**")

  if os.path.exists(DATA_FILE):
    try:
      df_mail_check = pd.read_csv(DATA_FILE)
      if not df_mail_check.empty and "Date" in df_mail_check.columns:
        df_mail_check = df_mail_check.dropna(subset=["Date"])
        df_mail_check["Date_dt"] = pd.to_datetime(
            df_mail_check["Date"], errors="coerce"
        )
        df_mail_check = df_mail_check.dropna(subset=["Date_dt"])

        if not df_mail_check.empty:
          df_mail_check["Month_Year"] = df_mail_check["Date_dt"].dt.strftime(
              "%B %Y"
          )
          mail_months = df_mail_check["Month_Year"].unique().tolist()

          if mail_months:
            selected_mail_month = st.selectbox(
                "Select Month for Email:", mail_months, key="sidebar_mail_month"
            )

            if st.button(
                "Get the Email", type="primary", use_container_width=True
            ):
              if selected_mail_month and str(selected_mail_month) != "nan":
                df_selected = df_mail_check[
                    df_mail_check["Month_Year"] == selected_mail_month
                ].copy()

                pivot_mail = df_selected.pivot_table(
                    index=["Date", "Time", "Heat No", "Operator"],
                    columns="Material",
                    values="Weight",
                    aggfunc="sum",
                    fill_value=0,
                ).reset_index()

                for m in MATERIALS:
                  if m not in pivot_mail.columns:
                    pivot_mail[m] = 0.0
                pivot_mail["Total Weight"] = pivot_mail[MATERIALS].sum(axis=1)

                chart_data_mail = []
                for m in MATERIALS:
                  mat_wt = (
                      pivot_mail[m].sum() if m in pivot_mail.columns else 0.0
                  )
                  count_heats = (
                      (pivot_mail[m] > 0).sum() if m in pivot_mail.columns else 1
                  )
                  if count_heats == 0:
                    count_heats = 1
                  avg_wt = mat_wt / count_heats
                  target_val = target_weights.get(m, 150.0)

                  if avg_wt == target_val and avg_wt > 0:
                    status = "🟢 अचूक (Green)"
                  elif avg_wt < target_val:
                    status = "🟡 कमी (Yellow)"
                  else:
                    status = "🔴 जास्त (Red)"

                  chart_data_mail.append({
                      "Material": m,
                      "Average Weight": avg_wt,
                      "Target": target_val,
                      "Status": status,
                  })

                df_chart_mail = pd.DataFrame(chart_data_mail)
                df_chart_mail["Status"] = pd.Categorical(
                    df_chart_mail["Status"],
                    categories=[
                        "🟢 अचूक (Green)",
                        "🟡 कमी (Yellow)",
                        "🔴 जास्त (Red)",
                    ],
                    ordered=True,
                )

                fig_mail = px.bar(
                    df_chart_mail,
                    x="Material",
                    y="Average Weight",
                    color="Status",
                    color_discrete_map={
                        "🟢 अचूक (Green)": "#28a745",
                        "🟡 कमी (Yellow)": "#ffc107",
                        "🔴 जास्त (Red)": "#dc3545",
                    },
                    title=f"Material Status Report - {selected_mail_month}",
                    category_orders={
                        "Status": [
                            "🟢 अचूक (Green)",
                            "🟡 कमी (Yellow)",
                            "🔴 जास्त (Red)",
                        ]
                    },
                )

                try:
                  img_bytes = fig_mail.to_image(format="png")
                except Exception as img_err:
                  img_bytes = None
                  print(f"Graph image generation error: {img_err}")

                csv_bytes = pivot_mail.to_csv(index=False).encode("utf-8")
                filename = f"Furnace_Report_{str(selected_mail_month).replace(' ', '_')}.csv"

                subject = (
                    f"📊 Furnace Heat Report & Graph - {selected_mail_month}"
                )
                body = (
                    f"Hello,\n\nPlease find attached the monthly furnace"
                    f" charging CSV report and visual graph analytics for"
                    f" {selected_mail_month}.\n\nTotal Records:"
                    f" {len(pivot_mail)}\nGrand Total Weight:"
                    f" {pivot_mail['Total Weight'].sum():.2f}"
                    f" Kg/Ton\n\nRegards,\nFurnace Charging System"
                )

                send_email_notification_async(
                    subject,
                    body,
                    file_to_attach=csv_bytes,
                    filename=filename,
                    image_bytes=img_bytes,
                    img_filename=f"Furnace_Graph_{str(selected_mail_month).replace(' ', '_')}.png",
                )
                st.success(
                    "Email with CSV Report and Graph Image sent successfully"
                    f" for {selected_mail_month}!"
                )
    except Exception as e:
      st.error(f"Error reading data for email: {e}")

st.markdown("---")

# --- 6. SAVED RECORDS & REPORT ---
st.subheader("🗓️ Month-wise Saved Report")

if os.path.exists(DATA_FILE):
  try:
    df_all = pd.read_csv(DATA_FILE)
    if not df_all.empty and "Date" in df_all.columns:
      df_all = df_all.dropna(subset=["Date"])
      df_all["Date_dt"] = pd.to_datetime(df_all["Date"], errors="coerce")
      df_all = df_all.dropna(subset=["Date_dt"])

      if not df_all.empty:
        df_all["Month_Year"] = df_all["Date_dt"].dt.strftime("%B %Y")
        all_months = df_all["Month_Year"].unique().tolist()

        if all_months:
          col_f1, col_f2 = st.columns([3, 1])
          with col_f1:
            selected_month = st.selectbox(
                "महिना निवडा (Select Month):", all_months
            )

          if selected_month and str(selected_month) != "nan":
            df_filtered = df_all[df_all["Month_Year"] == selected_month].copy()

            if not df_filtered.empty:
              pivot_df = df_filtered.pivot_table(
                  index=["Date", "Time", "Heat No", "Operator"],
                  columns="Material",
                  values="Weight",
                  aggfunc="sum",
                  fill_value=0,
              ).reset_index()

              for m in MATERIALS:
                if m not in pivot_df.columns:
                  pivot_df[m] = 0.0

              pivot_df["Total Weight"] = pivot_df[MATERIALS].sum(axis=1)

              display_df = pivot_df.copy()
              for m in MATERIALS:
                display_df[m] = display_df[m].apply(
                    lambda x: f"{x:.2f}" if float(x) > 0 else ""
                )
              display_df["Total Weight"] = display_df["Total Weight"].apply(
                  lambda x: f"{x:.2f}"
              )

              final_cols = (
                  ["Date", "Time", "Heat No", "Operator"]
                  + MATERIALS
                  + ["Total Weight"]
              )
              display_df = display_df[final_cols]

              st.markdown(
                  "<h4 style='text-align: center;'>Saved Records Data"
                  " Table</h4>",
                  unsafe_allow_html=True,
              )
              st.dataframe(display_df, use_container_width=True)

              # --- 📈 GRAPHICAL ANALYTICS SECTION (3-Color Status Graph & Table) ---
              st.markdown(
                  "<h4 style='text-align: center;'>📈 Visual Analytics &"
                  " Graphs (Date-wise Filter)</h4>",
                  unsafe_allow_html=True,
              )

              # Date filter for graph view
              available_dates = pivot_df["Date"].unique().tolist()
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
                count_heats = (
                    (df_graph_source[m] > 0).sum()
                    if m in df_graph_source.columns
                    else 1
                )
                if count_heats == 0:
                  count_heats = 1
                avg_wt = mat_wt / count_heats
                target_val = target_weights.get(m, 150.0)

                # Difference calculation
                diff = avg_wt - target_val

                # Status check: Green, Yellow, Red
                if avg_wt == target_val and avg_wt > 0:
                  status = "🟢 अचूक (Green)"
                elif avg_wt < target_val:
                  status = "🟡 कमी (Yellow)"
                else:
                  status = "🔴 जास्त (Red)"

                # Label for bar chart
                if avg_wt > 0:
                  diff_str = (
                      f"+{diff:.1f} kg" if diff > 0 else f"{diff:.1f} kg"
                  )
                  text_label = f"{avg_wt:.1f}\n({diff_str})"
                else:
                  text_label = "0.0"

                chart_data.append({
                    "Material": m,
                    "Average Weight": avg_wt,
                    "Target Weight": target_val,
                    "Difference (Kg)": f"{diff:+.1f} kg",
                    "Status": status,
                    "Text_Label": text_label,
                })

              df_chart = pd.DataFrame(chart_data)

              # Force 3-color categories
              df_chart["Status"] = pd.Categorical(
                  df_chart["Status"],
                  categories=[
                      "🟢 अचूक (Green)",
                      "🟡 कमी (Yellow)",
                      "🔴 जास्त (Red)",
                  ],
                  ordered=True,
              )

              # 1. Plotly Bar Chart Display
              fig = px.bar(
                  df_chart,
                  x="Material",
                  y="Average Weight",
                  color="Status",
                  text="Text_Label",
                  color_discrete_map={
                      "🟢 अचूक (Green)": "#28a745",
                      "🟡 कमी (Yellow)": "#ffc107",
                      "🔴 जास्त (Red)": "#dc3545",
                  },
                  title=(
                      "मटेरियलनुसार वजन स्टेटस व फरक (3-Color Status Graph)"
                  ),
                  category_orders={
                      "Status": [
                          "🟢 अचूक (Green)",
                          "🟡 कमी (Yellow)",
                          "🔴 जास्त (Red)",
                      ]
                  },
              )

              fig.update_traces(
                  texttemplate="%{text}",
                  textposition="auto",
              )
              st.plotly_chart(fig, use_container_width=True)

              # 2. Data Breakdown Table Below Graph
              st.markdown("### 📋 Material Breakdown & Difference Table")
              table_display = df_chart[
                  [
                      "Material",
                      "Average Weight",
                      "Target Weight",
                      "Difference (Kg)",
                      "Status",
                  ]
              ].copy()
              table_display["Average Weight"] = table_display[
                  "Average Weight"
              ].apply(lambda x: f"{x:.2f} kg")
              table_display["Target Weight"] = table_display[
                  "Target Weight"
              ].apply(lambda x: f"{x:.2f} kg")

              st.dataframe(table_display, use_container_width=True)

              # Heat-wise Line Chart
              if not df_graph_source.empty:
                heat_chart_df = (
                    df_graph_source[["Heat No", "Total Weight"]]
                    .set_index("Heat No")
                    .sort_index()
                )
                st.write("**हिटनुसार एकूण वजन (Total Weight per Heat):**")
                st.line_chart(heat_chart_df)

              grand_total = df_graph_source["Total Weight"].sum()

              col_t1, col_t2 = st.columns([2, 2])
              with col_t1:
                csv_data = df_graph_source.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Report (CSV)",
                    data=csv_data,
                    file_name=(
                        "Furnace_Report_"
                        f"{str(selected_month).replace(' ', '_')}.csv"
                    ),
                    mime="text/csv",
                )
              with col_t2:
                st.markdown(
                    f"<h4 style='text-align: right; color:"
                    f" #1E88E5;'>Grand Total: {grand_total:.2f}</h4>",
                    unsafe_allow_html=True,
                )
  except Exception as e:
    st.error(f"Error loading report: {e}")
else:
  st.info("अद्याप कोणतेही रेकॉर्ड सेव्ह केलेले नाही.")