import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime

# --- تنظیمات سیستمی ---
st.set_page_config(page_title="پنل جامع مرخصی رازکو", page_icon="🏢", layout="wide")

# تابع برای هش کردن پسورد (امنیت)
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# --- دیتابیس ---
conn = sqlite3.connect('razco_pro.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, role TEXT, balance INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS leaves(id INTEGER PRIMARY KEY, username TEXT, type TEXT, start DATE, end DATE, days INTEGER, status TEXT, reason TEXT)')
    # ایجاد یوزر ادمین پیش‌فرض اگر وجود نداشته باشد
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute('INSERT INTO users VALUES (?,?,?,?)', ('admin', make_hashes('razco123'), 'Admin', 999))
    conn.commit()

create_tables()

# --- استایل CSS اختصاصی رازکو ---
st.markdown("""
    <style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { font-family: 'Vazir', sans-serif; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #d32f2f; color: white; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e3141, #1e2130); }
    </style>
    """, unsafe_allow_html=True)

# --- مدیریت نشست (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['role'] = ''

# --- صفحه لاگین ---
def login_page():
    st.title("🏢 ورود به سامانه داخلی رازکو")
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("لطفاً مشخصات خود را وارد کنید")
            username = st.text_input("نام کاربری")
            password = st.text_input("رمز عبور", type='password')
            if st.button("ورود به پنل"):
                c.execute('SELECT * FROM users WHERE username = ?', (username,))
                user_data = c.fetchone()
                if user_data and check_hashes(password, user_data[1]):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = user_data[2]
                    st.success(f"خوش آمدید {username}")
                    st.rerun()
                else:
                    st.error("نام کاربری یا رمز عبور اشتباه است")

# --- پنل کارمند ---
def employee_dashboard():
    st.sidebar.title(f"👤 کارمند: {st.session_state['username']}")
    menu = ["پیشخوان", "ثبت درخواست مرخصی", "تاریخچه من"]
    choice = st.sidebar.selectbox("منو", menu)

    c.execute('SELECT balance FROM users WHERE username=?', (st.session_state['username'],))
    balance = c.fetchone()[0]

    if choice == "پیشخوان":
        st.header("📊 وضعیت مرخصی شما")
        st.metric("مانده مرخصی استحقاقی (روز)", balance)
        
        df_my = pd.read_sql_query("SELECT type, start, end, status FROM leaves WHERE username=?", conn, params=(st.session_state['username'],))
        if not df_my.empty:
            fig = px.pie(df_my, names='status', title="وضعیت درخواست‌های من", hole=0.3)
            st.plotly_chart(fig)
        else:
            st.info("هنوز درخواستی ثبت نکرده‌اید.")

    elif choice == "ثبت درخواست مرخصی":
        st.header("📝 فرم درخواست مرخصی")
        with st.form("leave_form"):
            l_type = st.selectbox("نوع مرخصی", ["استحقاقی", "استعلاجی", "بدون حقوق"])
            col1, col2 = st.columns(2)
            start_d = col1.date_input("از تاریخ")
            end_d = col2.date_input("تا تاریخ")
            reason = st.text_area("علت مرخصی")
            submit = st.form_submit_button("ارسال درخواست")
            
            if submit:
                days = (end_d - start_d).days + 1
                if l_type == "استحقاقی" and days > balance:
                    st.error(f"خطا! شما فقط {balance} روز مرخصی دارید اما {days} روز درخواست دادید.")
                else:
                    c.execute("INSERT INTO leaves (username, type, start, end, days, status, reason) VALUES (?,?,?,?,?,?,?)",
                              (st.session_state['username'], l_type, start_d, end_d, days, "در انتظار تایید", reason))
                    conn.commit()
                    st.success("درخواست شما با موفقیت ثبت شد و در صف تایید قرار گرفت.")

    elif choice == "تاریخچه من":
        st.header("📜 سوابق مرخصی")
        df_history = pd.read_sql_query("SELECT type, start, end, days, status FROM leaves WHERE username=?", conn, params=(st.session_state['username'],))
        st.table(df_history)

# --- پنل مدیریت (Admin) ---
def admin_dashboard():
    st.sidebar.title("🚩 پنل مدیریت رازکو")
    menu = ["مانیتورینگ کلی", "تایید درخواست‌ها", "مدیریت کاربران"]
    choice = st.sidebar.selectbox("منو", menu)

    if choice == "مانیتورینگ کلی":
        st.header("📈 داشبورد مدیریتی")
        df_all = pd.read_sql_query("SELECT * FROM leaves", conn)
        if not df_all.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(df_all, x='username', y='days', color='status', title="توزیع مرخصی نفرات"))
            with c2:
                st.plotly_chart(px.pie(df_all, names='type', title="انواع مرخصی در شرکت"))
            st.write("لیست کامل تراکنش‌ها:")
            st.dataframe(df_all)
        else:
            st.info("دیتایی وجود ندارد.")

    elif choice == "تایید درخواست‌ها":
        st.header("⚖️ بررسی درخواست‌های باز")
        pending = pd.read_sql_query("SELECT * FROM leaves WHERE status='در انتظار تایید'", conn)
        if not pending.empty:
            for i, row in pending.iterrows():
                with st.expander(f"درخواست {row['username']} - {row['days']} روز"):
                    st.write(f"علت: {row['reason']}")
                    st.write(f"بازه: {row['start']} تا {row['end']}")
                    col_t, col_r = st.columns(2)
                    if col_t.button("✅ تایید نهایی", key=f"t{row['id']}"):
                        # کسر از موجودی اگر استحقاقی بود
                        if row['type'] == "استحقاقی":
                            c.execute("UPDATE users SET balance = balance - ? WHERE username = ?", (row['days'], row['username']))
                        c.execute("UPDATE leaves SET status='تایید شده' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
                    if col_r.button("❌ رد درخواست", key=f"r{row['id']}"):
                        c.execute("UPDATE leaves SET status='رد شده' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
        else:
            st.success("هیچ درخواستی در صف تایید نیست.")

    elif choice == "مدیریت کاربران":
        st.header("👥 تعریف کارمند جدید")
        new_user = st.text_input("نام کاربری جدید")
        new_pass = st.text_input("رمز عبور جدید", type='password')
        new_bal = st.number_input("سهمیه مرخصی سالانه (روز)", value=20)
        if st.button("ثبت کارمند در سیستم رازکو"):
            try:
                c.execute("INSERT INTO users VALUES (?,?,?,?)", (new_user, make_hashes(new_pass), 'Employee', new_bal))
                conn.commit()
                st.success(f"کاربر {new_user} با موفقیت ایجاد شد.")
            except:
                st.error("این نام کاربری قبلاً ثبت شده!")

# --- منطق اصلی اجرای برنامه ---
if not st.session_state['logged_in']:
    login_page()
else:
    st.sidebar.button("خروج از سامانه", on_click=lambda: st.session_state.update({'logged_in': False}))
    if st.session_state['role'] == 'Admin':
        admin_dashboard()
    else:
        employee_dashboard()
