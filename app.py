import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Furnace Charging System", layout="wide")

DATA_FILE = "heat_records.csv"

# सर्व मटरेलची यादी
MATERIALS = ["MS", "CRC", "CI", "PIG", "SG BORING", "CI BORING", "SOLED", "R.R"]

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
            else:
                st.warning("कृपया ऑपरेटरचे नाव टाका!")
    st.stop()

# ऑपरेटर बॅनर
col_op1, col_op2 = st.columns([4, 1])
with col_op1:
    st.success(f"**सक्रिय ऑपरेटर (Active Operator):** {st.session_state['operator_name']}")
with col_op2:
    if st.button("Logout", type="primary"):
        st.session_state["operator_name"] = ""
        st.rerun()

# --- २. सिस्टीम फ्लोचार्ट ---
with st.expander("📌 System Process Flowchart", expanded=False):
    st.graphviz_chart('''
        digraph {
            rankdir=LR;
            node [shape=box, style=filled, fillcolor=lightcyan, fontname="Arial"];
            A [label="👤 Operator Login", fillcolor=lightyellow]
            B [label="📅 Check Today's Date"]
            C [label="🔥 Auto Heat No (1, 2, 3...)"]
            D [label="💾 Save Entry"]
            E [label="📊 Daily & Monthly Report", fillcolor=lightgreen]
            
            A -> B -> C -> D -> E
        }
    ''')

st.markdown("---")

# --- ३. एका दिवसातील Auto Increment & Next Day Reset Heat No Logic ---
def get_next_heat_no():
    if not os.path.exists(DATA_FILE):
        return 1
    try:
        df = pd.read_csv(DATA_FILE)
        if df.empty or "Date" not in df.columns or "Heat No" not in df.columns:
            return 1
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # आजच्या तारखेचा डेटा फिल्टर करा
        df_today = df[df["Date"] == today_str]
        
        if df_today.empty:
            # जर आज नवीन दिवस असेल, तर १ पासून सुरू करा
            return 1
        else:
            # जर आजच्या दिवशी आधी एंट्रिज असतील, तर सर्वात मोठ्या Heat No मध्ये +1 करा
            max_heat = df_today["Heat No"].max()
            return int(max_heat) + 1
    except Exception:
        return 1

suggested_heat_no = get_next_heat_no()

# --- ४. Charging Entry Form ---
col_h1, col_h2 = st.columns([2, 2])
with col_h1:
    # ऑटोमॅटिक पुढील नंबर येईल (हवा असल्यास बदलू शकता)
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
        st.warning("कृपया कमीत कमी एका Material चे नाव आणि Weight भरा!")
    else:
        now = datetime.now()
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
                "Weight": wt
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
        st.success(f"✅ Heat No {int(current_heat_no)} ची माहिती सेव्ह झाली!")
        st.rerun()

st.markdown("---")

# --- ५. Saved Records & Month Report ---
st.subheader("🗓️ Month-wise Saved Report")

if os.path.exists(DATA_FILE):
    df_all = pd.read_csv(DATA_FILE)
    
    if not df_all.empty and "Date" in df_all.columns:
        df_all["Date_dt"] = pd.to_datetime(df_all["Date"])
        df_all["Month_Year"] = df_all["Date_dt"].dt.strftime("%B %Y")
        
        all_months = df_all["Month_Year"].unique().tolist()
        
        col_f1, col_f2 = st.columns([3, 1])
        with col_f1:
            selected_month = st.selectbox("महिना निवडा (Select Month):", all_months)
        
        df_filtered = df_all[df_all["Month_Year"] == selected_month].copy()
        
        if not df_filtered.empty:
            pivot_df = df_filtered.pivot_table(
                index=["Date", "Time", "Heat No", "Operator"],
                columns="Material",
                values="Weight",
                aggfunc="sum",
                fill_value=0
            ).reset_index()
            
            for m in MATERIALS:
                if m not in pivot_df.columns:
                    pivot_df[m] = 0.0
                    
            pivot_df["Total Weight"] = pivot_df[MATERIALS].sum(axis=1)
            
            display_df = pivot_df.copy()
            for m in MATERIALS:
                display_df[m] = display_df[m].apply(lambda x: f"{x:.2f}" if x > 0 else "")
            display_df["Total Weight"] = display_df["Total Weight"].apply(lambda x: f"{x:.2f}")
            
            final_cols = ["Date", "Time", "Heat No", "Operator"] + MATERIALS + ["Total Weight"]
            display_df = display_df[final_cols]
            
            st.markdown("<h4 style='text-align: center;'>Saved Records Data Table</h4>", unsafe_allow_html=True)
            st.dataframe(display_df, use_container_width=True)
            
            grand_total = pivot_df["Total Weight"].sum()
            
            col_t1, col_t2 = st.columns([2, 2])
            with col_t1:
                csv_data = pivot_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Month Report (CSV)",
                    data=csv_data,
                    file_name=f"Furnace_Report_{selected_month.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
            with col_t2:
                st.markdown(
                    f"<h4 style='text-align: right; color: #1E88E5;'>Grand Total: {grand_total:.2f}</h4>", 
                    unsafe_allow_html=True
                )
else:
    st.info("अद्याप कोणतेही रेकॉर्ड सेव्ह केलेले नाही.")