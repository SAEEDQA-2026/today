import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from hijri_converter import Gregorian
import io, os, json
import streamlit.components.v1 as components

# --- 1. الإعدادات ---
st.set_page_config(page_title="المستشار المالي 2026 - v57", layout="wide")

DB_FILE = "finance_master_2026.csv"
CONFIG_FILE = "app_config_persistent.json"

DAILY_CATS = ["بنزين", "ماء", "الزيت", "الغاز", "السيارة", "تصليح", "فواتير", "مقاضي البيت", "مقاهي", "خضاروفواكهه", "مخالفات", "مقاضي البنات", "المستشفيات والصيدليات", "مطاعم", "ترفيه وحجوزات", "خدمات خارجية", "قطات", "عناية", "أخرى"]
INCOME_CATS = ["الراتب", "حساب المواطن", "الدعم السكني", "الاسهم", "مسترجعات", "حقوق خاصة", "العمالة", "انتداب", "اركابات", "أخرى"]
FIXED_CATS = ["القرض الشخصي", "القرض", "القرض العقاري", "امي", "كفالة", "الاعاشة"]

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"goal": 5000, "services": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(config, f)

config = load_config()

# --- 2. الحماية ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>🔒 نظام الإدارة المالية 2026</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.text_input("أدخل رمز الدخول", type="password") == "33550":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. المحرك ---
def get_salary_day(year, month):
    try:
        t_27 = date(int(year), int(month), 27)
        return 26 if t_27.weekday() == 4 else (28 if t_27.weekday() == 5 else 27)
    except: return 27

def get_fiscal_cycle(dt):
    if pd.isna(dt): return "None"
    sd = get_salary_day(dt.year, dt.month)
    if dt.day >= sd: return (dt + pd.DateOffset(months=1)).strftime("%m-%Y")
    return dt.strftime("%m-%Y")

def get_cycle_range(cycle_str):
    try:
        month, year = map(int, cycle_str.split('-'))
        curr_month_start = date(year, month, 1)
        prev_month_end = curr_month_start - timedelta(days=1)
        start_day = get_salary_day(prev_month_end.year, prev_month_end.month)
        start_date = date(prev_month_end.year, prev_month_end.month, start_day)
        end_day = get_salary_day(year, month)
        end_date = date(year, month, end_day) - timedelta(days=1)
        return start_date, end_date
    except: return None, None

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df['التاريخ'] = pd.to_datetime(df['التاريخ'], errors='coerce')
            df['المبلغ'] = pd.to_numeric(df['المبلغ'], errors='coerce').fillna(0)
            return df.dropna(subset=['التاريخ']).reset_index(drop=True)
        except: pass
    return pd.DataFrame(columns=['التاريخ', 'اليوم', 'النوع', 'التصنيف', 'المبلغ', 'التفاصيل'])

def save_data(df): df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 4. الستايل (CSS) ---
st.markdown("""
<style>
    /* بطاقات زرقاء شفافة */
    .glass-card {
        background: rgba(30, 58, 138, 0.4);
        border-radius: 15px; padding: 20px; text-align: center;
        border: 1px solid #3b82f6; margin-bottom: 10px; height: 180px;
    }
    .lbl { color: #bfdbfe; font-size: 16px; font-weight: bold; margin-bottom: 5px; }
    
    /* القيم الرقمية (مع حدود سوداء للنص) */
    .val-pos { 
        color: #22c55e !important; font-size: 42px !important; font-weight: 900 !important;
        text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; 
    }
    .val-neg { 
        color: #ef4444 !important; font-size: 42px !important; font-weight: 900 !important;
        text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
    }
    .val-neu { color: #ffffff !important; font-size: 42px !important; font-weight: 900 !important; }
    
    /* صندوق التحذير */
    .warn-box {
        background-color: #7f1d1d; color: white; padding: 5px; border-radius: 5px;
        font-weight: bold; font-size: 13px; margin-top: 10px; animation: flash 1.5s infinite;
    }
    @keyframes flash { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
    
    /* إحصائيات الذروة */
    .stat-box { padding: 15px; border-radius: 12px; text-align: center; color: white; margin-bottom: 10px; }
    .stat-val { font-size: 28px; font-weight: 900; margin: 5px 0; }
    
    /* ملحوظات الخدمات (واضحة وعريضة) */
    .service-note-box {
        background: rgba(255,255,255,0.1); 
        padding: 10px; 
        border-radius: 8px;
        margin-top: 10px; 
        color: #ffffff; 
        font-weight: 900; /* خط عريض جداً */
        font-size: 15px;
        border: 1px solid rgba(255,255,255,0.3);
    }
</style>
""", unsafe_allow_html=True)

def get_hijri():
    t = date.today()
    h = Gregorian(t.year, t.month, t.day).to_hijri()
    days = {"Saturday":"السبت", "Sunday":"الأحد", "Monday":"الإثنين", "Tuesday":"الثلاثاء", "Wednesday":"الأربعاء", "Thursday":"الخميس", "Friday":"الجمعة"}
    return days.get(t.strftime("%A"),""), f"{t.year}/{t.month:02d}/{t.day:02d} | {h.year}/{h.month:02d}/{h.day:02d}"

d_name, d_full = get_hijri()
st.markdown(f"""<div style="background:#0f172a; padding:20px; border-radius:15px; text-align:center; border-bottom:4px solid #3b82f6;">
<h1 style='color:white; margin:0;'>{d_name}</h1><h2 style='color:#3b82f6; margin:0;'>{d_full}</h2></div>""", unsafe_allow_html=True)

# --- 5. المنطق ---
df = st.session_state.df
if not df.empty: df['دورة_الميزانية'] = df['التاريخ'].apply(get_fiscal_cycle)

tabs = st.tabs(["📊 الرئيسية", "🛒 مصروف", "💰 دخل", "🔄 مقارنات", "⚙️ إدارة"])

with tabs[0]:
    if not df.empty:
        # الحسابات
        in_all = df[df['النوع'].isin(['دخل', 'الدخل'])]['المبلغ'].sum()
        out_all = df[~df['النوع'].isin(['دخل', 'الدخل'])]['المبلغ'].sum()
        net_savings = in_all - out_all
        
        cycles = sorted([c for c in df['دورة_الميزانية'].unique() if c != "None"], key=lambda x: datetime.strptime(x, "%m-%Y"), reverse=True)
        sel_cycle = st.selectbox("📅 الدورة الشهرية:", cycles)
        curr_df = df[df['دورة_الميزانية'] == sel_cycle]
        
        m_inc = curr_df[curr_df['النوع'].isin(['دخل', 'الدخل'])]['المبلغ'].sum()
        m_exp = curr_df[~curr_df['النوع'].isin(['دخل', 'الدخل'])]['المبلغ'].sum()
        m_rem = m_inc - m_exp

        # --- البطاقات العلوية ---
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='glass-card'><div style='font-size:30px;'>💰</div><div class='lbl'>إجمالي الدخل</div><div class='val-neu' style='color:#1e40af !important;'>{m_inc:,.2f}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='glass-card'><div style='font-size:30px;'>💸</div><div class='lbl'>مصروفات الشهر</div><div class='val-neu' style='color:#7c3aed !important;'>{m_exp:,.2f}</div></div>", unsafe_allow_html=True)
        with c3:
            cls, warn = ("val-pos", "") if m_rem >= 0 else ("val-neg", "<div class='warn-box'>⚠️ عجز مالي!</div>")
            st.markdown(f"<div class='glass-card'><div style='font-size:30px;'>⚖️</div><div class='lbl'>المتبقي الشهري</div><div class='{cls}'>{m_rem:,.2f}</div>{warn}</div>", unsafe_allow_html=True)
        with c4:
            cls_n, warn_n = ("val-pos", "") if net_savings >= 0 else ("val-neg", "<div class='warn-box'>⚠️ رصيد سالب!</div>")
            st.markdown(f"<div class='glass-card'><div style='font-size:30px;'>🏦</div><div class='lbl'>صافي المدخرات</div><div class='{cls_n}'>{net_savings:,.2f}</div>{warn_n}</div>", unsafe_allow_html=True)

        st.divider()
        # --- استعادة إحصائيات الذروة (الطلب الأول) ---
        st.write("### 📈 إحصائيات النشاط والذروة")
        daily_spend = curr_df[~curr_df['النوع'].isin(['دخل', 'الدخل'])].groupby(curr_df['التاريخ'].dt.date)['المبلغ'].sum()
        ch, cl, cz = st.columns(3)
        
        # حساب الأيام الصفرية
        start_d, end_d = get_cycle_range(sel_cycle)
        zero_days = 0
        if start_d and end_d:
            total_days = (end_d - start_d).days + 1
            zero_days = max(0, total_days - len(daily_spend))

        if not daily_spend.empty:
            with ch: st.markdown(f"<div class='stat-box' style='background:linear-gradient(45deg, #7f1d1d, #b91c1c);'>🔺 أعلى صرف يومي<div class='stat-val'>{daily_spend.max():,.2f}</div>{daily_spend.idxmax()}</div>", unsafe_allow_html=True)
            with cl: st.markdown(f"<div class='stat-box' style='background:linear-gradient(45deg, #064e3b, #047857);'>🔻 أدنى صرف يومي<div class='stat-val'>{daily_spend.min():,.2f}</div>{daily_spend.idxmin()}</div>", unsafe_allow_html=True)
        
        with cz: st.markdown(f"<div class='stat-box' style='background:linear-gradient(45deg, #1e3a8a, #3b82f6);'>✨ أيام خالية من الصرف<div class='stat-val'>{zero_days}</div>يوم</div>", unsafe_allow_html=True)

        st.divider()
        st.write("### 🛠️ الخدمات والهدف (بدون مبالغ)")
        
        cw, cg, co, cgl = st.columns(4)
        for name, icon, col in [("ماء", "💧", cw), ("الغاز", "🔥", cg), ("الزيت", "🛢️", co)]:
            svc_data = config.get("services", {}).get(name, {"date": "---", "note": "لا توجد ملحوظة"})
            with col:
                # تم حذف القيمة المالية وجعل النص أبيض وعريض
                st.markdown(f"""<div style='background:#1e293b; padding:15px; border-radius:15px; text-align:center; border:2px solid #3b82f6;'>
                    <h2 style='color:white; font-weight:900;'>{icon} {name}</h2>
                    <div class='service-note-box'>📅 {svc_data['date']}<br>📝 {svc_data['note']}</div>
                </div>""", unsafe_allow_html=True)
                with st.popover(f"تعديل {name}"):
                    d_n = st.date_input("تاريخ", date.today(), key=f"d_{name}")
                    n_n = st.text_input("تفاصيل", value=svc_data['note'], key=f"n_{name}")
                    if st.button("حفظ", key=f"b_{name}"):
                        if "services" not in config: config["services"] = {}
                        config["services"][name] = {"date": d_n.strftime('%Y-%m-%d'), "note": n_n}
                        save_config(config); st.rerun()
        
        with cgl:
            cur_g = config.get("goal", 5000); g1, g2 = st.columns([3,1])
            new_g = g1.number_input("الهدف", value=cur_g, step=500, label_visibility="collapsed")
            if g2.button("💾"): config["goal"] = new_g; save_config(config); st.toast("حفظ")
            clr_g = "#22c55e" if m_rem >= cur_g else "#ef4444"
            st.markdown(f"""<div style='background:#1e293b; padding:15px; border-radius:15px; text-align:center; border:2px solid {clr_g};'>
            <h2 style='color:white;'>🎯 الهدف المالي</h2><h2 style='color:{clr_g};'>{m_rem:,.2f} / {cur_g:,.2f}</h2></div>""", unsafe_allow_html=True)

        st.divider()
        st.write(f"### 📊 إحصائيات {sel_cycle}")
        cp, cl = st.columns([1, 1.5])
        with cp:
            if not curr_df[~curr_df['النوع'].isin(['دخل', 'الدخل'])].empty:
                st.plotly_chart(px.pie(curr_df[~curr_df['النوع'].isin(['دخل', 'الدخل'])], values='المبلغ', names='التصنيف', hole=0.5, template="plotly_dark"), use_container_width=True)
        with cl: st.dataframe(curr_df.sort_values('التاريخ', ascending=False), use_container_width=True)

# --- Tab 4: مقارنات ---
with tabs[3]:
    if not df.empty:
        st.subheader("📈 مسار الترند")
        target = st.selectbox("🔍 اختر البند:", sorted(df['التصنيف'].unique()))
        idf = df[df['التصنيف'] == target].copy().sort_values('التاريخ')
        if not idf.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=idf['التاريخ'], y=idf['المبلغ'], mode='lines+markers', line=dict(color='#3b82f6', width=5, shape='spline'), marker=dict(size=10, color='white', line=dict(width=2, color='#3b82f6'))))
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)
        st.divider()
        pivot = df.pivot_table(index='التصنيف', columns='دورة_الميزانية', values='المبلغ', aggfunc='sum').fillna(0)
        sel = st.multiselect("حدد العناصر:", pivot.index.tolist(), default=pivot.index.tolist()[:10])
        if sel: st.dataframe(pivot.loc[sel].style.format("{:,.2f}"), use_container_width=True)

# --- Tab 5: السجلات ---
with tabs[4]:
    st.subheader("⚙️ إدارة السجلات")
    up = st.file_uploader("📥 استيراد ملف")
    if up:
        try:
            n_df = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
            n_df['التاريخ'] = pd.to_datetime(n_df['التاريخ'], errors='coerce')
            combined = pd.concat([st.session_state.df, n_df], ignore_index=True)
            clean = combined.drop_duplicates(subset=['التاريخ', 'التصنيف', 'المبلغ', 'النوع', 'التفاصيل'], keep='first')
            st.session_state.df = clean.reset_index(drop=True); save_data(st.session_state.df); st.success("تم!")
            st.rerun()
        except: st.error("خطأ!")
    st.divider()
    ed = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 حفظ"): st.session_state.df = ed; save_data(ed); st.success("تم!"); st.rerun()

# --- إدخال ---
with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("i"):
            st.subheader("💰 دخل"); d=st.date_input("تاريخ"); c=st.selectbox("مصدر", INCOME_CATS); a=st.number_input("مبلغ")
            if st.form_submit_button("حفظ"): st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"التاريخ":pd.to_datetime(d),"اليوم":d_name,"النوع":"دخل","التصنيف":c,"المبلغ":a}])], ignore_index=True); save_data(st.session_state.df); st.rerun()
    with c2:
        with st.form("f"):
            st.subheader("🏠 ثابت"); d=st.date_input("تاريخ"); c=st.selectbox("نوع", FIXED_CATS); a=st.number_input("مبلغ")
            if st.form_submit_button("حفظ"): st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"التاريخ":pd.to_datetime(d),"اليوم":d_name,"النوع":"مصروفات ثابتة","التصنيف":c,"المبلغ":a}])], ignore_index=True); save_data(st.session_state.df); st.rerun()

with tabs[1]:
    with st.form("d"):
        st.subheader("🛒 مصروف"); c1,c2,c3,c4=st.columns(4)
        d=c1.date_input("تاريخ"); c=c2.selectbox("تصنيف", DAILY_CATS); a=c3.number_input("مبلغ"); n=c4.text_input("تفاصيل")
        if st.form_submit_button("حفظ"): st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"التاريخ":pd.to_datetime(d),"اليوم":d_name,"النوع":"مصروف","التصنيف":c,"المبلغ":a,"التفاصيل":n}])], ignore_index=True); save_data(st.session_state.df); st.rerun()