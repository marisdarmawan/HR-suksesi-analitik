import streamlit as st
import os

# Import regex filter dari config agar metrik akurat
from config import KEYWORDS_STAFF_REGEX 

# ----------------------------------------------------------
# 1. IMPORT MODUL INTERNAL
# ----------------------------------------------------------
from data.data_loader import get_hr_data
from components.ews_view import render_ews_tab
from components.succession_view import render_succession_tab
from components.kpi_view import render_kpi_tab
from components.macro_analytics_view import render_macro_analytics_tab
from components.profile_card import render_search_results
from components.chatbot_view import render_chatbot_tab

# ----------------------------------------------------------
# 2. KONFIGURASI HALAMAN & STYLING
# ----------------------------------------------------------
st.set_page_config(
    page_title="HR Analytics Dashboard - PLN",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Membaca CSS dari file eksternal agar app.py bersih
def load_css(file_name="style.css"):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
            
load_css()

# ----------------------------------------------------------
# 3. INITIALIZE DATA (Diproses di layer data_loader)
# ----------------------------------------------------------
with st.spinner("Sinkronisasi Database HR PLN... Mohon Tunggu."):
    # Mengambil semua dataframe yang sudah dibersihkan dalam bentuk Dictionary
    db = get_hr_data() 

# ----------------------------------------------------------
# 4. SIDEBAR: FILTER GLOBAL & PENCARIAN
# ----------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Tower 5 Analytics")
    st.caption("Dashboard Perencanaan Suksesi Jabatan Struktural PLN")

    # Ambil list unit dari DataFrame HCBP
    daftar_unit = sorted(db['hcbp']['UNIT INDUK'].dropna().unique().tolist()) if not db['hcbp'].empty else []
    
    st.markdown("🏢 **Filter Unit Induk**")
    selected_unit = st.selectbox(
        "Tampilkan data khusus untuk unit:",
        ["-- Semua Unit --"] + daftar_unit
    )

    if selected_unit != "-- Semua Unit --":
        st.success(f"🔒 Filter aktif: **{selected_unit}**")

    st.divider()
    
    st.markdown("🔍 **Pencarian Global**")
    search_query = st.text_input("Cari Nama Pegawai atau Jabatan:")
    
    st.divider()
    st.caption("Sumber acuan: Perdir PT PLN No. 0050/2023")

# ----------------------------------------------------------
# 5. ROUTING HALAMAN (MAIN AREA)
# ----------------------------------------------------------
# Jika user mengetik sesuatu di Search Engine
if search_query:
    st.markdown(f"## 🔍 Hasil Pencarian untuk: `{search_query}`")
    # Panggil fungsi render dari komponen pencarian
    render_search_results(search_query, selected_unit, db)

# Jika Search Engine kosong, tampilkan Dashboard Normal
else:
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Tower 5 — Perencanaan Suksesi Analitik</h1>
        <p>Dashboard Monitoring Suksesi Jabatan Struktural PLN</p>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================================
    # FILTER DATA BERDASARKAN UNIT KERJA DI SIDEBAR (UNTUK METRIK)
    # ==========================================================
    df_pegawai_aktif = db['pegawai'].copy()
    df_profiler_aktif = db['profiler'].copy()
    
    if selected_unit != "-- Semua Unit --":
        # Filter dataframe pegawai berdasarkan unit
        df_pegawai_aktif = df_pegawai_aktif[df_pegawai_aktif['Company Name'].str.upper() == selected_unit.upper()]
        
        # Filter dataframe profiler/talenta berdasarkan unit
        if 'Company Name' in df_profiler_aktif.columns:
            df_profiler_aktif = df_profiler_aktif[df_profiler_aktif['Company Name'].str.upper() == selected_unit.upper()]

    # ==========================================================
    # HITUNG METRIK DINAMIS BERDASARKAN DATA TERFILTER
    # ==========================================================
    total_pegawai = len(df_pegawai_aktif)

    # Hitung hanya posisi struktural yang butuh suksesi pada unit terpilih
    df_kosong = df_pegawai_aktif[df_pegawai_aktif['Status_EWS'] != 'Aman']
    df_kosong_struktural = df_kosong[~df_kosong['Jabatan'].str.lower().str.contains(KEYWORDS_STAFF_REGEX, regex=True, na=False)]
    total_ews_struktural = len(df_kosong_struktural)

    # Hitung total kandidat yang available dan unggul pada unit terpilih
    kandidat_tersedia = len(df_profiler_aktif[df_profiler_aktif['Status_Ketersediaan'] == 'Available'])

    # Render Metrik di Main Page dengan 3 Kolom
    st.divider()
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.metric(label="👥 Total Pegawai Terpantau", value=f"{total_pegawai:,}".replace(',', '.'))
    with col_m2:
        st.metric(label="🚨 Posisi Struktural Kosong/EWS", value=f"{total_ews_struktural:,}".replace(',', '.'))
    with col_m3:
        st.metric(label="⭐ Talent Pool Tersedia", value=f"{kandidat_tersedia:,}".replace(',', '.'))
    st.divider()

    # ==========================================================
    # TABS UTAMA DASHBOARD
    # ==========================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 Asisten AI",
        "🚨 EWS Pensiun & Masa Jabatan", 
        "🎯 Suksesi Jabatan", 
        "📈 Analitik KPI", 
        "🚁 Analitik Makro" 
    ])

    # Lempar data (db) dan filter (selected_unit) ke masing-masing komponen
    with tab1:
        render_chatbot_tab()
    with tab2:
        render_ews_tab(db, selected_unit)
    with tab3:
        render_succession_tab(db, selected_unit)
    with tab4:
        render_kpi_tab(db, selected_unit)
    with tab5: 
        render_macro_analytics_tab(db, selected_unit)