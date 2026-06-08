import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================
# 1. KONFIGURASI & LOAD DATA
# ==========================
st.set_page_config(page_title="Dashboard Perencanaan Suksesi Analitik", page_icon="📊", layout="wide")

@st.cache_data
def load_data():
    # Load tabel master pegawai
    df = pd.read_csv('Synthetic_Data_Pegawai_Patched.csv', low_memory=False)
    
    # Tanggal referensi berdasarkan 'Tanggal Export Data' di dataset (21 Mei 2026)
    tanggal_sekarang = pd.to_datetime('2026-05-21')
    
    # --- Perhitungan EWS Pensiun ---
    df['Sisa Waktu Pensiun (Tahun)'] = 56 - df['Umur Tahun']
    
    def kategori_pensiun(umur):
        if umur >= 56: return "Pensiun / MPP"
        elif umur == 55: return "1 Tahun Lagi"
        elif umur in [53, 54]: return "2-3 Tahun Lagi"
        else: return "Aman (> 3 Tahun)"
    df['Status Pensiun'] = df['Umur Tahun'].apply(kategori_pensiun)
    
    # --- Perhitungan EWS Masa Jabatan (Tenure) ---
    df['Start Date Jabatan'] = pd.to_datetime(df['Start Date Jabatan'], errors='coerce')
    # Menghitung durasi jabatan dalam hitungan tahun
    df['Masa Jabatan (Tahun)'] = (tanggal_sekarang - df['Start Date Jabatan']).dt.days / 365.25
    
    def kategori_tenure(masa):
        if pd.isna(masa): return "Data Tidak Valid"
        elif masa >= 5: return "Kritis (> 5 Tahun)"
        elif masa >= 4: return "Warning (4-5 Tahun)"
        else: return "Aman (< 4 Tahun)"
    df['Status Masa Jabatan'] = df['Masa Jabatan (Tahun)'].apply(kategori_tenure)
    
    return df

df_pegawai = load_data()

# ==========================
# 2. SIDEBAR: FILTER GLOBAL
# ==========================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Logo_PLN.png/960px-Logo_PLN.png", width=150)
st.sidebar.header("Filter Organisasi")

list_area = ["Semua Area"] + sorted(df_pegawai['Personal Area'].dropna().unique().tolist())
selected_area = st.sidebar.selectbox("Pilih Personal Area", list_area)

if selected_area != "Semua Area":
    df_filtered = df_pegawai[df_pegawai['Personal Area'] == selected_area]
else:
    df_filtered = df_pegawai

st.title("📊 Dashboard Perencanaan Suksesi Analitik")
st.markdown("Dasbor ini mengakomodir *monitoring* usia pensiun, masa jabatan (rotasi), dan pencarian *backup* kandidat berdasarkan kualifikasi struktural.")

# ==========================
# 3. TABS NAVIGASI
# ==========================
tab1, tab2, tab3 = st.tabs(["⚠️ EWS Pensiun", "🔄 EWS Masa Jabatan (Rotasi)", "🔍 Pencarian Backup Kandidat"])

# -----------------------------------
# TAB 1: EWS PENSIUN
# -----------------------------------
with tab1:
    st.header("Early Warning System: Batas Usia Pensiun")
    df_ews_pensiun = df_filtered[df_filtered['Umur Tahun'] >= 53]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Pensiun / MPP (Usia >= 56)", len(df_ews_pensiun[df_ews_pensiun['Status Pensiun'] == "Pensiun / MPP"]))
    col2.metric("Pensiun 1 Tahun Lagi", len(df_ews_pensiun[df_ews_pensiun['Status Pensiun'] == "1 Tahun Lagi"]))
    col3.metric("Pensiun 2-3 Tahun Lagi", len(df_ews_pensiun[df_ews_pensiun['Status Pensiun'] == "2-3 Tahun Lagi"]))
    
    col_chart1, col_chart2 = st.columns([1, 2])
    with col_chart1:
        fig_pie_pensiun = px.pie(df_ews_pensiun, names='Status Pensiun', title="Proporsi Status Pensiun", hole=0.4)
        st.plotly_chart(fig_pie_pensiun, use_container_width=True)
        
    with col_chart2:
        profesi_pensiun = df_ews_pensiun['Kode dan Dahan Profesi'].value_counts().head(10).reset_index()
        profesi_pensiun.columns = ['Dahan Profesi', 'Jumlah Pegawai']
        fig_bar_pensiun = px.bar(profesi_pensiun, x='Jumlah Pegawai', y='Dahan Profesi', orientation='h', title="Top 10 Dahan Profesi Terdampak Pensiun")
        fig_bar_pensiun.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar_pensiun, use_container_width=True)

    st.dataframe(df_ews_pensiun[['NIP', 'Nama Lengkap', 'Jabatan', 'Personal Area', 'Umur Tahun', 'Status Pensiun']].sort_values(by='Umur Tahun', ascending=False), use_container_width=True, hide_index=True)

# -----------------------------------
# TAB 2: EWS MASA JABATAN (ROTASI)
# -----------------------------------
with tab2:
    st.header("Early Warning System: Kebutuhan Rotasi (Masa Jabatan)")
    st.markdown("Memantau pegawai yang menempati posisi yang sama lebih dari 4 tahun untuk mitigasi *stagnancy* dan kebutuhan penyegaran organisasi.")
    
    df_ews_tenure = df_filtered[df_filtered['Masa Jabatan (Tahun)'] >= 4].copy()
    
    col1, col2 = st.columns(2)
    col1.metric("Status Kritis (> 5 Tahun di Jabatan Sama)", len(df_ews_tenure[df_ews_tenure['Status Masa Jabatan'] == "Kritis (> 5 Tahun)"]))
    col2.metric("Status Warning (4 - 5 Tahun)", len(df_ews_tenure[df_ews_tenure['Status Masa Jabatan'] == "Warning (4-5 Tahun)"]))
    
    # Histogram Distribusi Masa Jabatan
    fig_hist = px.histogram(df_filtered[df_filtered['Masa Jabatan (Tahun)'] > 0], x="Masa Jabatan (Tahun)", 
                            nbins=20, title="Distribusi Masa Jabatan Pegawai", color="Status Masa Jabatan")
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.subheader("Daftar Pegawai Membutuhkan Rotasi Segera")
    df_ews_tenure['Masa Jabatan (Tahun)'] = df_ews_tenure['Masa Jabatan (Tahun)'].round(1)
    st.dataframe(df_ews_tenure[['NIP', 'Nama Lengkap', 'Jabatan', 'Level PHDP', 'Personal Area', 'Masa Jabatan (Tahun)', 'Status Masa Jabatan']].sort_values(by='Masa Jabatan (Tahun)', ascending=False), use_container_width=True, hide_index=True)

# -----------------------------------
# TAB 3: PROYEKSI BACKUP KANDIDAT
# -----------------------------------
with tab3:
    st.header("Pencarian & Proyeksi Backup Kandidat")
    st.markdown("Cari kandidat internal berdasarkan parameter struktural untuk mengisi potensi jabatan kosong.")
    
    c1, c2, c3 = st.columns(3)
    
    # Pilihan Rumpun Profesi (menggunakan kolom 'Kode dan Dahan Profesi')
    list_profesi = ["Semua Dahan Profesi"] + sorted(df_pegawai['Kode dan Dahan Profesi'].dropna().unique().tolist())
    filter_profesi = c1.selectbox("Filter Dahan Profesi", list_profesi)
    
    # Pilihan Level PHDP (sebagai proksi eselon/grade)
    list_phdp = ["Semua Level"] + sorted(df_pegawai['Level PHDP'].dropna().unique().tolist())
    filter_phdp = c2.selectbox("Filter Level PHDP", list_phdp)
    
    # Pilihan Jenis Pendidikan
    list_pendidikan = ["Semua Latar Belakang"] + sorted(df_pegawai['Jenis Pendidikan'].dropna().unique().tolist())
    filter_pendidikan = c3.selectbox("Filter Tingkat Pendidikan", list_pendidikan)
    
    # Aplikasikan filter kandidat
    df_kandidat = df_filtered.copy()
    if filter_profesi != "Semua Dahan Profesi":
        df_kandidat = df_kandidat[df_kandidat['Kode dan Dahan Profesi'] == filter_profesi]
    if filter_phdp != "Semua Level":
        df_kandidat = df_kandidat[df_kandidat['Level PHDP'] == filter_phdp]
    if filter_pendidikan != "Semua Latar Belakang":
        df_kandidat = df_kandidat[df_kandidat['Jenis Pendidikan'] == filter_pendidikan]
    
    # Kecualikan mereka yang sebentar lagi pensiun dari daftar kandidat (filter umur <= 52)
    df_kandidat = df_kandidat[df_kandidat['Umur Tahun'] <= 52]
    
    st.success(f"Ditemukan **{len(df_kandidat)}** kandidat potensial yang memenuhi kriteria (dan belum memasuki masa EWS pensiun).")
    
    kolom_kandidat = ['NIP', 'Nama Lengkap', 'Jabatan', 'Level PHDP', 'Kode dan Nama Profesi', 'Jenis Pendidikan', 'Nama Jurusan', 'Masa Jabatan (Tahun)']
    if not df_kandidat.empty:
        df_kandidat['Masa Jabatan (Tahun)'] = df_kandidat['Masa Jabatan (Tahun)'].round(1)
        st.dataframe(df_kandidat[kolom_kandidat].sort_values(by='Level PHDP'), use_container_width=True, hide_index=True)
