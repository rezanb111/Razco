import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- تنظیمات صفحه و ظاهر نئونی رازکو ---
st.set_page_config(page_title="سیستم مرخصی رازکو", layout="wide")

st.markdown("""
    <style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { font-family: 'Vazir', sans-serif; direction: rtl; text-align: right; }
    .stApp { background-color: #0b0e14; color: #00f2ff; }
    .stButton>button { background: linear-gradient(45deg, #00f2ff, #0066ff); color: white; border-radius: 10px; border: none; box-shadow: 0 0 15px #00f2ff; }
    div[data-testid="stExpander"] { background: rgba(255, 255, 255, 0.05); border: 1px solid #00f2ff; border-radius: 10px; }
    .footer { position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; font-size: 12px; color: #555; }
    </style>
    <div class="footer">حقوق این سایت متعلق به شرکت رازکو می‌باشد</div>
    """, unsafe_allow_html=True)

# --- دیتابیس ---
conn = sqlite3.connect('razco_v2.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users(id_code TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS leaves(id INTEGER PRIMARY KEY, id_code TEXT, name TEXT, start DATE, end DATE, status TEXT)')
# ساخت ادمین اول
c.execute("SELECT * FROM users WHERE id_code='000'")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES ('000', '123', 'مدیر رازکو', 'Admin')")
conn.commit()

# --- سیستم ورود ---
if 'user' not in st.session_state:
    st.title("🏢 ورود به سامانه رازکو")
    tab1, tab2 = st.tabs(["ورود", "ثبت‌نام کارمند جدید"])
    
    with tab1:
        u = st.text_input("کد ملی")
        p = st.text_input("رمز عبور", type="password")
        if st.button("ورود"):
            c.execute("SELECT * FROM users WHERE id_code=? AND password=?", (u, p))
            user = c.fetchone()
            if user:
                st.session_state.user = user
                st.rerun()
            else: st.error("اشتباهه!")

    with tab2:
        new_id = st.text_input("کد ملی جدید")
        new_name = st.text_input("نام و نام خانوادگی")
        new_p = st.text_input("رمز عبور", type="password", key="p2")
        if st.button("ثبت‌نام"):
            try:
                c.execute("INSERT INTO users VALUES (?,?,?,?)", (new_id, new_p, new_name, 'Employee'))
                conn.commit()
                st.success("حالا وارد شو!")
            except: st.error("تکراریه!")

# --- بعد از ورود ---
else:
    user = st.session_state.user
    st.sidebar.title(f"خوش آمدی {user[2]}")
    if st.sidebar.button("خروج"):
        del st.session_state.user
        st.rerun()

    # --- پنل کارمند (ثبت درخواست) ---
    if user[3] == 'Employee':
        st.header("📝 ثبت درخواست مرخصی")
        with st.form("leave_form"):
            d1 = st.date_input("از تاریخ")
            d2 = st.date_input("تا تاریخ")
            if st.form_submit_button("ارسال درخواست"):
                c.execute("INSERT INTO leaves (id_code, name, start, end, status) VALUES (?,?,?,?,?)", 
                          (user[0], user[2], str(d1), str(d2), "در انتظار تایید"))
                conn.commit()
                st.success("درخواست فرستاده شد واسه مدیر.")
        
        st.subheader("وضعیت درخواست‌های من")
        my_leaves = pd.read_sql(f"SELECT start, end, status FROM leaves WHERE id_code='{user[0]}'", conn)
        st.table(my_leaves)

    # --- پنل ادمین (تایید یا رد) ---
    elif user[3] == 'Admin':
        st.header("👑 پنل مدیریت رازکو")
        st.subheader("درخواست‌های جدید کارمندان")
        pending = pd.read_sql("SELECT * FROM leaves WHERE status='در انتظار تایید'", conn)
        
        if pending.empty:
            st.info("فعلاً خبری نیست!")
        else:
            for i, row in pending.iterrows():
                with st.expander(f"درخواست از: {row['name']} ({row['start']} تا {row['end']})"):
                    c1, c2 = st.columns(2)
                    if c1.button("✅ تایید", key=f"ok_{row['id']}"):
                        c.execute("UPDATE leaves SET status='تایید شده' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
                    if c2.button("❌ رد", key=f"no_{row['id']}"):
                        c.execute("UPDATE leaves SET status='رد شده' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
