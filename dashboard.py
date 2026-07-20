import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re

# ==========================================================
# KONFIGURASI HALAMAN & STYLING
# ==========================================================
st.set_page_config(
    page_title="HR Analytics Dashboard - PLN",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Warna aksen utama mengikuti identitas PLN */
    :root { --pln-blue: #00A2E9; --pln-navy: #0C2340; }

    /* Header halaman */
    .main-header {
        padding: 1.25rem 1.75rem;
        border-radius: 12px;
        background: linear-gradient(90deg, var(--pln-navy) 0%, var(--pln-blue) 100%);
        margin-bottom: 1.25rem;
    }
    .main-header h1 {
        color: #FFFFFF;
        margin-bottom: 0.15rem;
        font-size: 1.7rem;
    }
    .main-header p {
        color: #E5F6FF;
        margin-bottom: 0;
        font-size: 0.95rem;
    }

    /* Kartu tips interaktif */
    .tips-box {
        background-color: #EAF7FF;
        border-left: 4px solid var(--pln-blue);
        padding: 0.65rem 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        font-size: 0.92rem;
        color: #0C2340;
    }

    /* Rapikan tab agar lebih besar & mudah dibaca */
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0 0;
        padding: 0 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--pln-blue);
        color: white;
    }

    /* Metric card (area utama) */
    div[data-testid="stMetric"] {
        background-color: #F7FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.9rem 1rem;
    }

    /* Sidebar: latar gelap */
    section[data-testid="stSidebar"] { background-color: #0C2340; }
    
    /* Ubah warna teks elemen tulisan di sidebar menjadi terang */
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] [data-testid="stMetricValue"],
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] { 
        color: #F5F9FF !important; 
    }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }

    /* Paksa input text berwarna gelap di atas putih agar selalu terlihat jelas */
    .stTextInput input {
        color: #0C2340 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
    }

    /* [PERBAIKAN] Metric card di dalam sidebar ukurannya disesuaikan */
    section[data-testid="stSidebar"] div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 10px;
        padding: 0.6rem 0.5rem; /* Padding dikurangi sedikit agar ruang lebih lega */
    }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.05rem !important; /* Font diperkecil dari 1.3rem */
        white-space: normal !important; /* Mencegah pemotongan teks dengan elipsis (...) */
        word-wrap: break-word !important; 
    }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: #B9D4EE !important;
        font-size: 0.85rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# DICTIONARY & HELPER: KLASIFIKASI RESMI PERDIR 0050/2023
# ==========================================================
def get_official_category(jabatan, grade=0, company_name=""):
    j = str(jabatan).lower()
    u = str(company_name).lower()
    grade = int(grade) if pd.notna(grade) else 0
    
    # 1. JALUR STRUKTURAL & GENERALIS TERTENTU
    if 'senior executive' in j or 'kepala satuan' in j or 'senior evp' in j: 
        return 'Manajemen Atas Khusus'
    if 'executive vice president' in j or 'general manager' in j or 'evp' in j or 'gm' in j: 
        return 'Manajemen Atas'
    if 'vice president' in j or 'senior manager' in j or 'vp' in j: 
        return 'Manajemen Menengah'
        
    if 'manager' in j and not any(x in j for x in ['assistant', 'asman', 'layanan', 'ulp', 'senior', 'general', 'executive', 'vp']):
        return 'Manajemen Dasar'
        
    if 'assistant manager' in j or 'asman' in j: 
        return 'Generalist 3 Tertentu (Asman/Mgr Layanan)'
        
    if 'manager' in j and ('layanan' in u or 'ulp' in u or 'ulp' in j or 'layanan' in j): 
        return 'Generalist 3 Tertentu (Asman/Mgr Layanan)'
        
    if 'team leader' in j: 
        return 'Generalist 2 Tertentu (Team Leader)'
    
    # 2. JALUR FUNGSIONAL SPESIALIS & GENERALIS (FSG)
    if grade >= 18: return 'Senior Specialist'
    if grade >= 15: return 'Specialist'
    if grade >= 13: return 'Generalist 3'
    if grade >= 11: return 'Generalist 2'
    return 'Generalist 1'

# FUNGSI CEK KELAYAKAN PROMOSI
def is_eligible(curr_cat, curr_grade, tgt_cat):
    curr_grade = int(curr_grade) if pd.notna(curr_grade) else 0
    if tgt_cat == 'Manajemen Atas Khusus':
        if curr_cat in ['Manajemen Atas Khusus', 'Manajemen Atas'] and curr_grade >= 20: return True
        if curr_cat == 'Senior Specialist' and curr_grade >= 20: return True
    elif tgt_cat == 'Manajemen Atas':
        if curr_cat in ['Manajemen Atas', 'Manajemen Menengah'] and curr_grade >= 17: return True
        if curr_cat == 'Senior Specialist' and curr_grade >= 18: return True
    elif tgt_cat == 'Manajemen Menengah':
        if curr_cat in ['Manajemen Menengah', 'Manajemen Dasar'] and curr_grade >= 14: return True
        if curr_cat in ['Senior Specialist', 'Specialist'] and curr_grade >= 15: return True
    elif tgt_cat == 'Manajemen Dasar':
        if curr_cat in ['Manajemen Dasar', 'Generalist 3 Tertentu (Asman/Mgr Layanan)'] and curr_grade >= 12: return True
        if curr_cat in ['Specialist', 'Generalist 3'] and curr_grade >= 13: return True
    elif tgt_cat == 'Generalist 3 Tertentu (Asman/Mgr Layanan)':
        if curr_cat in ['Generalist 3 Tertentu (Asman/Mgr Layanan)', 'Generalist 2 Tertentu (Team Leader)'] and curr_grade >= 10: return True
        if curr_cat in ['Generalist 3', 'Generalist 2'] and curr_grade >= 11: return True
    elif tgt_cat == 'Generalist 2 Tertentu (Team Leader)':
        if curr_cat == 'Generalist 2 Tertentu (Team Leader)' and curr_grade >= 8: return True
        if curr_cat in ['Generalist 2', 'Generalist 1'] and curr_grade >= 8: return True
    return False 

@st.cache_data
def load_and_process_hr_data():
    pegawai = pd.read_csv('Synthetic_Data_Pegawai_Patched.csv', low_memory=False)
    kinerja = pd.read_csv('Synthetic_Data_Kinerja.csv')
    assessment = pd.read_csv('Synthetic_Data_Hasil_Assessment_Psikologis_Potensi.csv')
    aps = pd.read_csv('Synthetic_APS_Data.csv')
    riwayat_jabatan = pd.read_csv('Synthetic_Riwayat_Jabatan_Patched.csv') 
    
    try:
        hcbp = pd.read_excel('Data HCBP.xlsx')
    except:
        hcbp = pd.DataFrame(columns=['UNIT INDUK', 'UNIT PELAKSANA'])
    
    try:
        simprod = pd.read_csv('Simprod_Flattened.csv')
    except:
        simprod = pd.DataFrame()

    pegawai = pegawai[pegawai['Umur Tahun'] <= 56].copy()
    pegawai['Start Date Jabatan'] = pd.to_datetime(pegawai['Start Date Jabatan'], errors='coerce')
    pegawai['Lama_Menjabat_Tahun'] = (pd.to_datetime('today') - pegawai['Start Date Jabatan']).dt.days / 365.25

    def hitung_status_ews_eksekutif(row):
        w = []
        if pd.notna(row['Umur Tahun']) and row['Umur Tahun'] >= 55: w.append("Mendekati Pensiun")
        jabatan_teks = str(row['Jabatan']).lower()
        
        # [PERBAIKAN] Menggunakan Regex Boundary \b agar EXE-CUTI-VE tidak terbaca sebagai "cuti"
        is_staff = bool(re.search(r'\b(?:officer|technician|tugas belajar|specialist|analyst|cuti)\b', jabatan_teks))
        if not is_staff:
            if pd.notna(row['Lama_Menjabat_Tahun']) and row['Lama_Menjabat_Tahun'] >= 4.0: w.append("Over SLA")
        return " | ".join(w) if w else "Aman"
    
    pegawai['Status_EWS'] = pegawai.apply(hitung_status_ews_eksekutif, axis=1)

    kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    assessment_latest = assessment.sort_values('Tanggal_Assessment_UPAC').drop_duplicates('NIP', keep='last')

    profiler = pegawai[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Business Area', 'Personal Sub Area', 'Kode dan Dahan Profesi', 'Person Grade']].copy()
    profiler = profiler.merge(kinerja_latest[['NIP', 'Name_Box_Talent', 'Nilai_Kinerja_Semester', 'Nilai_Assessment_UPAC']], on='NIP', how='left')
    
    profiler['Career_Level'] = profiler.apply(
        lambda x: get_official_category(x['Jabatan'], x['Person Grade'], x['Company Name']), axis=1
    )
    
    dimensi_31 = ['CEE', 'BAC', 'DCM', 'DOR', 'PNO', 'BTR', 'COL', 'BPA', 'INF', 'ADA', 'CLE', 'COC', 'CIM', 'EXE', 'FCH', 'IOT', 'ABS', 'NUM', 'VER', 'I', 'F', 'A', 'C', 'E', 'S', 'COM', 'TMW', 'SEF', 'INI', 'DEC', 'SER']
    kolom_tarik = ['NIP'] + dimensi_31
    profiler = profiler.merge(assessment_latest[kolom_tarik], on='NIP', how='left')

    nips_dalam_aps = aps['NIP'].unique()
    # [PERBAIKAN] Regex Boundary untuk pengecekan Availability
    kondisi_tidak_tersedia = profiler['NIP'].isin(nips_dalam_aps) | profiler['Jabatan'].str.lower().str.contains(r'\b(?:cuti|tugas belajar)\b', regex=True, na=False)
    profiler['Status_Ketersediaan'] = np.where(kondisi_tidak_tersedia, 'Not Available (APS / Cuti / Tugas Belajar)', 'Available')

    return pegawai, profiler, aps, simprod, kinerja, hcbp, riwayat_jabatan

with st.spinner("Sinkronisasi Database HR PLN... Mohon Tunggu."):
    pegawai, profiler, aps, simprod, kinerja, hcbp, riwayat_jabatan = load_and_process_hr_data()

# ==========================================================
# SIDEBAR: SEARCH ENGINE & RINGKASAN
# ==========================================================
with st.sidebar:
    st.markdown("### ⚡ Tower 5 Analytics")
    st.caption("Dashboard Perencanaan Suksesi Jabatan Struktural PLN")

    # --- FILTER UNIT GLOBAL (daftar unit diambil dari Master HCBP) ---
    st.markdown("🏢 **Filter Unit Induk**")
    daftar_unit_induk = sorted(hcbp['UNIT INDUK'].dropna().unique().tolist()) if not hcbp.empty else []
    list_unit_filter = ["-- Semua Unit --"] + daftar_unit_induk
    selected_unit_filter = st.selectbox(
        "Tampilkan data khusus untuk unit:",
        list_unit_filter,
        key="global_unit_filter"
    )

    if selected_unit_filter != "-- Semua Unit --":
        st.success(f"🔒 Filter aktif: **{selected_unit_filter}**")

    st.divider()
    
    # --- GLOBAL SEARCH ENGINE ---
    st.markdown("🔍 **Pencarian Global**")
    search_query = st.text_input("Cari Nama Pegawai atau Jabatan:")
    if selected_unit_filter != "-- Semua Unit --":
        st.caption(f"🔎 Pencarian dibatasi hanya di dalam unit **{selected_unit_filter}**.")
    
    st.divider()

    # Terapkan filter unit global ke ringkasan data
    if selected_unit_filter != "-- Semua Unit --":
        pegawai_f = pegawai[pegawai['Company Name'].str.upper() == selected_unit_filter.upper()].copy()
        profiler_f = profiler[profiler['Company Name'].str.upper() == selected_unit_filter.upper()].copy()
    else:
        pegawai_f = pegawai
        profiler_f = profiler

    total_pegawai = len(pegawai_f)
    total_ews = int((pegawai_f['Status_EWS'] != 'Aman').sum())
    total_unit = pegawai_f['Company Name'].nunique()

    st.markdown("**📊 Ringkasan Data Terkini**")
    c1, c2 = st.columns(2)
    c1.metric("Total Pegawai", f"{total_pegawai:,}")
    c2.metric("Kasus EWS", f"{total_ews:,}")
    st.metric("Unit Induk Terpantau", f"{total_unit}")

    st.divider()
    st.caption("Sumber acuan: Perdir PT PLN No. 0050/2023")

# ==========================================================
# FUNGSI RENDER PROFIL (BISA DIPAKAI BERULANG)
# ==========================================================
def render_profil_eksekutif(data_talent, target_career_level=None):
    col_profil, col_radar = st.columns([1.2, 1.5]) 
    with col_profil:
        # [PERBAIKAN] Menambahkan print Nama Lengkap di dalam profil!
        st.markdown(f"**Nama Lengkap:** {data_talent['Nama Lengkap']}")
        st.markdown(f"**NIP:** `{data_talent['NIP']}`")
        st.markdown(f"**Jabatan Saat Ini:** {data_talent['Jabatan']} ({data_talent['Company Name']})")
        st.markdown(f"**Grade:** {data_talent['Person Grade']} | **Status Kapasitas:** {data_talent['Career_Level']}")
        
        bt = data_talent['Name_Box_Talent'] if pd.notna(data_talent['Name_Box_Talent']) else "Data Belum Tersedia"
        st.info(f"📊 **9-Box Talent Placement:** {bt}")
        
        dimensi_31 = ['CEE', 'BAC', 'DCM', 'DOR', 'PNO', 'BTR', 'COL', 'BPA', 'INF', 'ADA', 'CLE', 'COC', 'CIM', 'EXE', 'FCH', 'IOT', 'ABS', 'NUM', 'VER', 'I', 'F', 'A', 'C', 'E', 'S', 'COM', 'TMW', 'SEF', 'INI', 'DEC', 'SER']
        skor_31_dimensi = int(data_talent[dimensi_31].fillna(0).sum())
        
        nks = data_talent['Nilai_Kinerja_Semester'] if pd.notna(data_talent['Nilai_Kinerja_Semester']) else 0
        nau = data_talent['Nilai_Assessment_UPAC'] if pd.notna(data_talent['Nilai_Assessment_UPAC']) else 0
        skor_final = int(nks + nau)
        
        st.success(f"⭐ **Total Assessment Psikologis (31 Dimensi):** {skor_31_dimensi}")
        st.success(f"⭐ **Skor Suksesi Final:** {skor_final}")
        st.caption(f"*(Gabungan dari **Kinerja Semester:** {nks} + **Assessment UPAC:** {nau})*")
        
        if target_career_level:
            st.markdown("---")
            st.markdown("💡 **Analisis Kelayakan Promosi:**")
            alasan_layak = f"Berdasarkan **Perdir PT PLN No. 0050/2023**, posisi kandidat saat ini sebagai **{data_talent['Career_Level']}** dengan **Person Grade {data_talent['Person Grade']}** memenuhi syarat *eligibility* mutlak untuk menduduki posisi **{target_career_level}**. Selain memenuhi kriteria kepatuhan administratif, kandidat sangat direkomendasikan karena masuk dalam kategori Talenta Unggul (**{bt}**) dan memiliki akumulasi skor Kinerja & Assessment yang sangat memuaskan (**{skor_final}**)."
            st.markdown(alasan_layak)
    
    with col_radar:
        kompetensi = {
            'CEE (Customer Focus)': data_talent['CEE'] if pd.notna(data_talent['CEE']) else 0,
            'DCM (Decision Making)': data_talent['DCM'] if pd.notna(data_talent['DCM']) else 0,
            'COM (Communication)': data_talent['COM'] if pd.notna(data_talent['COM']) else 0,
            'BAC (Business Acumen)': data_talent['BAC'] if pd.notna(data_talent['BAC']) else 0,
            'DOR (Drive for Result)': data_talent['DOR'] if pd.notna(data_talent['DOR']) else 0,
            'INI (Initiative)': data_talent['INI'] if pd.notna(data_talent['INI']) else 0,
            'DEC (Decisiveness)': data_talent['DEC'] if pd.notna(data_talent['DEC']) else 0,
            'SEF (Self Confidence)': data_talent['SEF'] if pd.notna(data_talent['SEF']) else 0
        }
        if sum(kompetensi.values()) == 0:
            st.warning("Belum ada data nilai assessment psikologis untuk kandidat ini.")
        else:
            df_radar = pd.DataFrame(dict(skor=list(kompetensi.values()), parameter=list(kompetensi.keys())))
            fig_radar = px.line_polar(df_radar, r='skor', theta='parameter', line_close=True, range_r=[0, 10])
            fig_radar.update_traces(fill='toself', line_color='#00A2E9')
            st.plotly_chart(fig_radar, use_container_width=True)

def render_riwayat_jabatan(nip_kandidat):
    st.divider()
    st.subheader("📜 Riwayat Perjalanan Karier")
    nip_col = 'NIP' if 'NIP' in riwayat_jabatan.columns else 'nip'
    df_riwayat_kandidat = riwayat_jabatan[riwayat_jabatan[nip_col] == nip_kandidat].copy()
    
    if not df_riwayat_kandidat.empty:
        if 'start_date' in df_riwayat_kandidat.columns:
            df_riwayat_kandidat['start_date_dt'] = pd.to_datetime(df_riwayat_kandidat['start_date'], errors='coerce')
        if 'end_date' in df_riwayat_kandidat.columns:
            df_riwayat_kandidat['end_date_dt'] = pd.to_datetime(df_riwayat_kandidat['end_date'], errors='coerce')
            
        sekarang = pd.to_datetime('today')
        def hitung_durasi(row):
            start = row.get('start_date_dt', pd.NaT)
            end = row.get('end_date_dt', sekarang) if pd.notna(row.get('end_date_dt')) else sekarang
            if pd.isna(start): return "-"
            delta = end - start
            tahun = delta.days // 365
            bulan = (delta.days % 365) // 30
            if tahun > 0: return f"{tahun} Thn {bulan} Bln"
            return f"{bulan} Bln"
            
        df_riwayat_kandidat['Durasi'] = df_riwayat_kandidat.apply(hitung_durasi, axis=1)
        
        def potong_org(org_val):
            if pd.isna(org_val): return "-"
            parts = [p.strip() for p in str(org_val).split('-')]
            return " - ".join(parts[:3])
        if 'organisasi' in df_riwayat_kandidat.columns:
            df_riwayat_kandidat['Organisasi (Max Level 3)'] = df_riwayat_kandidat['organisasi'].apply(potong_org)
            
        df_riwayat_kandidat['Mulai Menjabat'] = df_riwayat_kandidat['start_date_dt'].dt.strftime('%d %b %Y').fillna('-') if 'start_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('start_date', '-')
        df_riwayat_kandidat['Akhir Menjabat'] = df_riwayat_kandidat['end_date_dt'].dt.strftime('%d %b %Y').fillna('Sekarang') if 'end_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('end_date', '-')
        
        if 'end_date_dt' in df_riwayat_kandidat.columns:
            df_riwayat_kandidat = df_riwayat_kandidat.sort_values(by='end_date_dt', ascending=False, na_position='first')
            
        kolom_tersedia = df_riwayat_kandidat.columns.tolist()
        kolom_final = [nip_col, 'Mulai Menjabat', 'Akhir Menjabat', 'Durasi']
        if 'jabatan' in kolom_tersedia: kolom_final.append('jabatan')
        if 'jenis jabatan' in kolom_tersedia: kolom_final.append('jenis jabatan')
        if 'jenjang jabatan' in kolom_tersedia: kolom_final.append('jenjang jabatan')
        if 'Organisasi (Max Level 3)' in df_riwayat_kandidat.columns: kolom_final.append('Organisasi (Max Level 3)')
        
        df_tampil = df_riwayat_kandidat[kolom_final].rename(columns={nip_col: 'NIP', 'jabatan': 'Jabatan', 'jenis jabatan': 'Jenis Jabatan', 'jenjang jabatan': 'Jenjang Jabatan'})
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada data riwayat jabatan yang ditemukan untuk kandidat ini.")

# ==========================================================
# RENDER TAMPILAN PENCARIAN ATAU DASHBOARD NORMAL
# ==========================================================
if search_query:
    st.markdown(f"## 🔍 Hasil Pencarian untuk: `{search_query}`")
    
    pegawai_matched = profiler_f[profiler_f['Nama Lengkap'].str.lower().str.contains(search_query.lower(), na=False)]
    jabatan_matched = pegawai_f[pegawai_f['Jabatan'].str.lower().str.contains(search_query.lower(), na=False)]
    
    # ------------------------------------------------------
    # PENCARIAN NAMA PEGAWAI
    # ------------------------------------------------------
    if not pegawai_matched.empty:
        st.success(f"Ditemukan {len(pegawai_matched)} Pegawai dengan kueri tersebut.")
        st.write("👉 **Klik pada baris pegawai di bawah ini untuk melihat detail profil dan rekomendasi promosi:**")
        
        df_tampil_peg = pegawai_matched[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name']].rename(columns={'Company Name': 'Unit Kerja'})
        event_peg = st.dataframe(df_tampil_peg, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="tbl_cari_pegawai")
        
        if len(event_peg.selection.rows) > 0:
            row = pegawai_matched.iloc[event_peg.selection.rows[0]]
            
            st.divider()
            st.markdown(f"### 👤 Profil Detail: {row['Nama Lengkap']}")
            render_profil_eksekutif(row)
            render_riwayat_jabatan(row['NIP'])
            
            # --- CEK REKOMENDASI PROMOSI ---
            if row['Status_Ketersediaan'] == 'Available' and row['Name_Box_Talent'] in ['Promotable', 'Solid Contributor', 'High Potential']:
                st.divider()
                st.subheader(f"🚀 Rekomendasi Promosi Jabatan")
                st.write(f"Berikut adalah posisi struktural yang saat ini sedang kosong/membutuhkan suksesi dan sesuai dengan kualifikasi jenjang karir **{row['Nama Lengkap']}**:")
                
                df_jab_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()
                # [PERBAIKAN] Regex Boundary
                df_jab_kosong = df_jab_kosong[~df_jab_kosong['Jabatan'].str.lower().str.contains(r'\b(?:officer|technician|tugas belajar|specialist|analyst|cuti)\b', regex=True, na=False)]
                
                jab_kosong_dahan = df_jab_kosong[df_jab_kosong['Kode dan Dahan Profesi'] == row['Kode dan Dahan Profesi']]
                
                layak_list = []
                for _, jrow in jab_kosong_dahan.iterrows():
                    tgt_cat = get_official_category(jrow['Jabatan'], 0, jrow['Company Name'])
                    if is_eligible(row['Career_Level'], row['Person Grade'], tgt_cat):
                        layak_list.append({
                            'Target Jabatan': jrow['Jabatan'],
                            'Unit Kerja': jrow['Company Name'],
                            'Area': jrow['Business Area'],
                            'Level Target': tgt_cat,
                            'Alasan Kosong': jrow['Status_EWS']
                        })
                
                if layak_list:
                    df_layak = pd.DataFrame(layak_list)
                    st.dataframe(df_layak, use_container_width=True, hide_index=True)
                    
                    st.markdown("💡 **Analisis Kelayakan Promosi:**")
                    alasan_layak = f"Berdasarkan **Perdir PT PLN No. 0050/2023**, posisi kandidat saat ini sebagai **{row['Career_Level']}** dengan **Person Grade {row['Person Grade']}** memenuhi syarat *eligibility* mutlak untuk menduduki posisi-posisi di atas. Selain memenuhi kriteria kepatuhan administratif, kandidat direkomendasikan karena masuk dalam kategori Talenta Unggul (**{row['Name_Box_Talent']}**)."
                    st.success(alasan_layak)
                else:
                    st.info("Saat ini tidak ada posisi struktural kosong di dahan profesi yang sama yang sesuai dengan jenjang karir kandidat ini.")

    # ------------------------------------------------------
    # PENCARIAN JABATAN
    # ------------------------------------------------------
    elif not jabatan_matched.empty:
        st.success(f"Ditemukan {len(jabatan_matched)} Posisi Jabatan yang mengandung kata '{search_query}'.")
        st.write("👉 **Klik pada baris jabatan di bawah ini untuk melihat profil pejabat saat ini dan status suksesi:**")
        
        df_tampil_jab = jabatan_matched[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Status_EWS']].rename(columns={'Nama Lengkap': 'Pejabat Saat Ini', 'Company Name': 'Unit Kerja'})
        event_jab = st.dataframe(df_tampil_jab, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="tbl_cari_jabatan")
        
        if len(event_jab.selection.rows) > 0:
            row = jabatan_matched.iloc[event_jab.selection.rows[0]]
            
            st.divider()
            st.markdown(f"### 🏢 Detail Posisi: {row['Jabatan']}")
            
            pejabat_skrg = profiler[profiler['NIP'] == row['NIP']]
            if not pejabat_skrg.empty:
                st.markdown("#### 👤 Pejabat Saat Ini:")
                render_profil_eksekutif(pejabat_skrg.iloc[0])
            else:
                st.warning("Data profil pejabat saat ini tidak ditemukan.")
            
            st.divider()
            
            # CEK KEBUTUHAN SUKSESI
            if row['Status_EWS'] != 'Aman':
                st.error(f"⚠️ Jabatan ini saat ini **MEMBUTUHKAN SUKSESI** (Status: {row['Status_EWS']})")
                
                dahan_profesi_target = row['Kode dan Dahan Profesi']
                nip_pejabat_saat_ini = row['NIP']
                target_jabatan = row['Jabatan']
                target_unit = row['Business Area']
                target_career_level = get_official_category(target_jabatan, 0, target_unit)

                st.subheader(f"👥 Daftar Calon Suksesor")
                st.caption(f"Target Posisi diidentifikasi sebagai **{target_career_level}**.")
                
                kandidat_pool = profiler[
                    (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
                    (profiler['NIP'] != nip_pejabat_saat_ini) &
                    (profiler['Name_Box_Talent'].isin(['Promotable', 'Solid Contributor', 'High Potential'])) &
                    (profiler['Status_Ketersediaan'] == 'Available')
                ].copy()
                 
                if not kandidat_pool.empty:
                    kandidat_pool = kandidat_pool[kandidat_pool.apply(lambda x: is_eligible(x['Career_Level'], x['Person Grade'], target_career_level), axis=1)]
                    
                    if not kandidat_pool.empty:
                        kandidat_pool['Nilai_Kinerja_Semester'] = kandidat_pool['Nilai_Kinerja_Semester'].fillna(0)
                        kandidat_pool['Nilai_Assessment_UPAC'] = kandidat_pool['Nilai_Assessment_UPAC'].fillna(0)
                        kandidat_pool['Skor_Suksesi_Final'] = kandidat_pool['Nilai_Kinerja_Semester'] + kandidat_pool['Nilai_Assessment_UPAC']
                        kandidat_pool = kandidat_pool.sort_values(by='Skor_Suksesi_Final', ascending=False)
                        
                        st.write("👉 **Klik kandidat di bawah ini untuk melihat detail (Level 4 & Riwayat Karir):**")
                        kolom_tampil = ['NIP', 'Nama Lengkap', 'Jabatan', 'Career_Level', 'Name_Box_Talent', 'Skor_Suksesi_Final']
                        event_kandidat = st.dataframe(kandidat_pool[kolom_tampil], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key=f"tbl_cand_jab_search")
                        
                        if len(event_kandidat.selection.rows) > 0:
                            data_talent_cand = kandidat_pool.iloc[event_kandidat.selection.rows[0]]
                            st.divider()
                            st.markdown(f"#### 🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent_cand['Nama Lengkap']}")
                            render_profil_eksekutif(data_talent_cand, target_career_level)
                            render_riwayat_jabatan(data_talent_cand['NIP'])
                    else:
                        st.error("⚠️ Kandidat yang tersedia tidak memenuhi syarat pola Jenjang Karir / Person Grade yang ditetapkan pada dokumen Peraturan Pelaksana.")
                else:
                    st.warning("Tidak ditemukan kandidat dengan Box Talent 'Promotable/Solid' yang satu dahan profesi dan berstatus Available.")

            else:
                st.success("✅ Jabatan ini saat ini terpantau **AMAN** dan belum membutuhkan suksesi mendesak.")
            st.markdown("---")

    else:
        st.warning("Tidak ditemukan hasil yang cocok dengan pencarian Anda.")

else:
    # ==========================================================
    # HEADER UTAMA DASHBOARD NORMAL (JIKA SEARCH KOSONG)
    # ==========================================================
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Tower 5 — Perencanaan Suksesi Analitik</h1>
        <p>Dashboard Monitoring Suksesi Jabatan Struktural PLN</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🚨  EWS Pensiun & Masa Jabatan", "🎯  Suksesi Jabatan & Profiler", "📈  Analitik KPI Unit & Pegawai"])

    # =========================================================================
    # TAB 1: DRILL-DOWN EARLY WARNING SYSTEM (EWS)
    # =========================================================================
    with tab1:
        st.header("🚨 Peta Kerawanan Suksesi Jabatan (EWS)")
        st.markdown('<div class="tips-box">💡 <b>Tips Interaktif:</b> Klik pada salah satu kotak di treemap atau baris tabel untuk menelusuri data secara mendalam (<i>Deep Dive</i>).</div>', unsafe_allow_html=True)
        if selected_unit_filter != "-- Semua Unit --":
            st.caption(f"🏢 Menampilkan data khusus untuk unit: **{selected_unit_filter}**")
        
        df_ews_aktif = pegawai_f[pegawai_f['Status_EWS'] != 'Aman'].copy()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Kasus EWS", f"{len(df_ews_aktif):,}")
        m2.metric("Mendekati Pensiun", f"{int(df_ews_aktif['Status_EWS'].str.contains('Pensiun').sum()):,}")
        m3.metric("Over SLA Jabatan", f"{int(df_ews_aktif['Status_EWS'].str.contains('Over SLA').sum()):,}")
        st.caption("ℹ️ Satu pegawai bisa masuk ke *kedua* kategori sekaligus (Mendekati Pensiun **dan** Over SLA).")
        st.divider()

        st.subheader("📊 Level 1: Jumlah Kasus EWS per Unit Induk")
        summary_unit_induk = df_ews_aktif.groupby('Company Name').size().reset_index(name='Jumlah Pegawai Alert')
        
        fig_ui = px.treemap(
            summary_unit_induk, path=['Company Name'], values='Jumlah Pegawai Alert',
            color='Jumlah Pegawai Alert', color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
            title="Jumlah Kasus EWS per Unit Induk"
        )
        fig_ui.update_traces(textinfo="label+value")
        fig_ui.update_layout(margin=dict(t=40, l=10, r=10, b=10))
        event_ui = st.plotly_chart(fig_ui, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_ews_ui")

        if len(event_ui.selection.points) > 0:
            selected_ui = event_ui.selection.points[0].get("label")

            st.divider()
            st.subheader(f"🏢 Level 2: Detail Sebaran di {selected_ui}")
            df_filtered_ui = df_ews_aktif[df_ews_aktif['Company Name'] == selected_ui]
            summary_pelaksana = df_filtered_ui.groupby(['Business Area', 'Personal Sub Area']).size().reset_index(name='Jumlah Kasus')
            
            fig_up = px.treemap(
                summary_pelaksana, path=['Business Area', 'Personal Sub Area'], values='Jumlah Kasus',
                color='Jumlah Kasus', color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
                title=f"Sebaran Kasus EWS di {selected_ui}"
            )
            fig_up.update_traces(textinfo="label+value")
            fig_up.update_layout(margin=dict(t=40, l=10, r=10, b=10))
            event_up = st.plotly_chart(fig_up, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_ews_up")

            if len(event_up.selection.points) > 0:
                pt_up = event_up.selection.points[0]
                clicked_label = pt_up.get("label")
                clicked_parent = pt_up.get("parent")

                if clicked_parent:
                    # Kotak anak (leaf) diklik -> Business Area = parent, Personal Sub Area = label
                    df_level3 = df_filtered_ui[
                        (df_filtered_ui['Business Area'] == clicked_parent) &
                        (df_filtered_ui['Personal Sub Area'] == clicked_label)
                    ].copy()
                    judul_level3 = clicked_label
                else:
                    # Kotak induk (Business Area) diklik langsung -> tampilkan semua di bawahnya
                    df_level3 = df_filtered_ui[df_filtered_ui['Business Area'] == clicked_label].copy()
                    judul_level3 = clicked_label

                st.divider()
                st.subheader(f"📋 Level 3: Daftar Personil Masuk Radar EWS di {judul_level3}")
                df_final_karyawan = df_level3
                df_final_karyawan['Lama_Menjabat_Tahun'] = df_final_karyawan['Lama_Menjabat_Tahun'].round(1)
                kolom_final = ['NIP', 'Nama Lengkap', 'Jabatan', 'Lama_Menjabat_Tahun', 'Umur Tahun', 'Status_EWS']
                st.dataframe(df_final_karyawan[kolom_final], use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2: SUKSESI JABATAN KOSONG
    # =========================================================================
    with tab2:
        st.header("🎯 Perencanaan Pengisian Jabatan Struktural (Suksesi)")
        st.markdown('<div class="tips-box">💡 <b>Tips Interaktif:</b> Klik pada kotak treemap atau baris tabel untuk menelusuri posisi kosong hingga memunculkan rekomendasi kandidat.</div>', unsafe_allow_html=True)
        if selected_unit_filter != "-- Semua Unit --":
            st.caption(f"🏢 Menampilkan data khusus untuk unit: **{selected_unit_filter}**")

        df_jabatan_kosong = pegawai_f[pegawai_f['Status_EWS'] != 'Aman'].copy()
        keywords_staff = ['officer', 'technician', 'tugas belajar', 'specialist', 'analyst', 'cuti']
        df_jabatan_kosong = df_jabatan_kosong[~df_jabatan_kosong['Jabatan'].str.lower().str.contains(r'\b(?:officer|technician|tugas belajar|specialist|analyst|cuti)\b', regex=True, na=False)]

        mv1, mv2 = st.columns(2)
        mv1.metric("Jumlah Jabatan Struktural Perlu Suksesi", f"{len(df_jabatan_kosong):,}")
        mv2.metric("Jumlah Unit Induk Perlu Suksesi", f"{df_jabatan_kosong['Company Name'].nunique():,}")
        st.divider()

        st.subheader("📊 Level 1: Proyeksi Lowongan Jabatan Struktural per Unit Induk")
        st.caption("Klik salah satu kotak pada treemap di bawah untuk melihat rincian posisi per Unit Induk.")
        summary_vacancy_ui = df_jabatan_kosong.groupby('Company Name').size().reset_index(name='Total Posisi Butuh Suksesi')
        summary_vacancy_ui = summary_vacancy_ui.sort_values(by='Total Posisi Butuh Suksesi', ascending=False)

        fig_vac_ui = px.treemap(
            summary_vacancy_ui, path=['Company Name'], values='Total Posisi Butuh Suksesi',
            color='Total Posisi Butuh Suksesi', color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
            title="Proyeksi Lowongan Jabatan Struktural per Unit Induk"
        )
        fig_vac_ui.update_traces(textinfo="label+value", texttemplate="%{label}<br>%{value} posisi")
        fig_vac_ui.update_layout(margin=dict(t=40, l=10, r=10, b=10))
        event_vac_ui = st.plotly_chart(fig_vac_ui, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_vacancy_ui")

        if len(event_vac_ui.selection.points) > 0:
            selected_vac_ui = event_vac_ui.selection.points[0].get("label")
            
            st.divider()
            st.subheader(f"🔍 Level 2: Detail Posisi Jabatan Struktural Terbuka di {selected_vac_ui}")
            df_filtered_vac = df_jabatan_kosong[df_jabatan_kosong['Company Name'] == selected_vac_ui]
            summary_vac_detail = df_filtered_vac.groupby(['Business Area', 'Personal Sub Area', 'Jabatan', 'Status_EWS', 'Kode dan Dahan Profesi', 'NIP']).size().reset_index(name='Kasus')
            summary_vac_detail.rename(columns={'Status_EWS': 'Alasan Kebutuhan Suksesi'}, inplace=True)
            
            event_vac_up = st.dataframe(summary_vac_detail[['Business Area', 'Personal Sub Area', 'Jabatan', 'Alasan Kebutuhan Suksesi']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

            if len(event_vac_up.selection.rows) > 0:
                idx_vac_up = event_vac_up.selection.rows[0]
                dahan_profesi_target = summary_vac_detail.iloc[idx_vac_up]['Kode dan Dahan Profesi']
                nip_pejabat_saat_ini = summary_vac_detail.iloc[idx_vac_up]['NIP']
                
                target_jabatan = summary_vac_detail.iloc[idx_vac_up]['Jabatan']
                target_unit = summary_vac_detail.iloc[idx_vac_up]['Business Area']
                
                # Identifikasi Target sesuai Perdir
                target_career_level = get_official_category(target_jabatan, 0, target_unit)

                st.divider()
                st.subheader(f"👥 Level 3: Kandidat Suksesor (Kesesuaian Dahan: {dahan_profesi_target})")
                st.caption(f"Target Posisi diidentifikasi sebagai **{target_career_level}**. Algoritma menyaring kandidat berdasarkan kepatuhan mutlak pada **Perdir No. 0050/2023 Pasal 3.3.8 & 3.3.9**.")
                
                kandidat_pool = profiler[
                    (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
                    (profiler['NIP'] != nip_pejabat_saat_ini) &
                    (profiler['Name_Box_Talent'].isin(['Promotable', 'Solid Contributor'])) &
                    (profiler['Status_Ketersediaan'] == 'Available')
                ].copy()
                
                if not kandidat_pool.empty:
                    # ==========================================================
                    # ALGORITMA KELAYAKAN SUKSESI (MURNI DARI PERDIR 0050/2023)
                    # ==========================================================
                    def is_eligible(curr_cat, curr_grade, tgt_cat):
                        curr_grade = int(curr_grade) if pd.notna(curr_grade) else 0
                        
                        if tgt_cat == 'Manajemen Atas Khusus':
                            if curr_cat in ['Manajemen Atas Khusus', 'Manajemen Atas'] and curr_grade >= 20: return True
                            if curr_cat == 'Senior Specialist' and curr_grade >= 20: return True
                            
                        elif tgt_cat == 'Manajemen Atas':
                            if curr_cat in ['Manajemen Atas', 'Manajemen Menengah'] and curr_grade >= 17: return True
                            if curr_cat == 'Senior Specialist' and curr_grade >= 18: return True
                            
                        elif tgt_cat == 'Manajemen Menengah':
                            if curr_cat in ['Manajemen Menengah', 'Manajemen Dasar'] and curr_grade >= 14: return True
                            if curr_cat in ['Senior Specialist', 'Specialist'] and curr_grade >= 15: return True
                            
                        elif tgt_cat == 'Manajemen Dasar':
                            if curr_cat in ['Manajemen Dasar', 'Generalist 3 Tertentu (Asman/Mgr Layanan)'] and curr_grade >= 12: return True
                            if curr_cat in ['Specialist', 'Generalist 3'] and curr_grade >= 13: return True
                            
                        elif tgt_cat == 'Generalist 3 Tertentu (Asman/Mgr Layanan)':
                            if curr_cat in ['Generalist 3 Tertentu (Asman/Mgr Layanan)', 'Generalist 2 Tertentu (Team Leader)'] and curr_grade >= 10: return True
                            if curr_cat in ['Generalist 3', 'Generalist 2'] and curr_grade >= 11: return True
                            
                        elif tgt_cat == 'Generalist 2 Tertentu (Team Leader)':
                            if curr_cat == 'Generalist 2 Tertentu (Team Leader)' and curr_grade >= 8: return True
                            if curr_cat in ['Generalist 2', 'Generalist 1'] and curr_grade >= 8: return True
                            
                        return False 
                    
                    kandidat_pool = kandidat_pool[kandidat_pool.apply(lambda x: is_eligible(x['Career_Level'], x['Person Grade'], target_career_level), axis=1)]
                    
                    if not kandidat_pool.empty:
                        kandidat_pool['Nilai_Kinerja_Semester'] = kandidat_pool['Nilai_Kinerja_Semester'].fillna(0)
                        kandidat_pool['Nilai_Assessment_UPAC'] = kandidat_pool['Nilai_Assessment_UPAC'].fillna(0)
                        
                        # Agregasi untuk sorting
                        kandidat_pool['Skor_Suksesi_Final'] = kandidat_pool['Nilai_Kinerja_Semester'] + kandidat_pool['Nilai_Assessment_UPAC']
                        kandidat_pool = kandidat_pool.sort_values(by='Skor_Suksesi_Final', ascending=False)
                        
                        # --- PODIUM TOP 3 KANDIDAT ---
                        st.markdown("#### 🏅 Top 3 Kandidat Rekomendasi")
                        st.caption("Klik nama kandidat pada kartu untuk langsung melihat profil lengkap (Level 4).")
                        top3 = kandidat_pool.head(3).reset_index(drop=True)
                        medali = [
                            {"emoji": "🥇", "warna": "#D4AF37", "label": "Kandidat #1"},
                            {"emoji": "🥈", "warna": "#A7A7AD", "label": "Kandidat #2"},
                            {"emoji": "🥉", "warna": "#CD7F32", "label": "Kandidat #3"},
                        ]
                        cols_podium = st.columns(3)
                        for i, col in enumerate(cols_podium):
                            with col:
                                if i < len(top3):
                                    cand = top3.iloc[i]
                                    gaya = medali[i]
                                    st.markdown(f"""
                                    <div style="background:linear-gradient(160deg,{gaya['warna']}30,{gaya['warna']}08);
                                                border:2px solid {gaya['warna']}; border-radius:14px;
                                                padding:1rem 0.75rem; text-align:center; margin-bottom:0.5rem;">
                                        <div style="font-size:2.1rem; line-height:1;">{gaya['emoji']}</div>
                                        <div style="font-weight:700; font-size:0.8rem; color:#0C2340; margin-top:0.25rem;">{gaya['label']}</div>
                                        <div style="font-size:1.7rem; font-weight:800; color:#0C2340;">{int(cand['Skor_Suksesi_Final'])}</div>
                                        <div style="font-size:0.75rem; color:#546881;">Skor Suksesi Final</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    if st.button(f"👤 {cand['Nama Lengkap']}", key=f"podium_{i}_{cand['NIP']}", use_container_width=True):
                                        st.session_state['selected_kandidat_nip'] = cand['NIP']
                                else:
                                    st.caption("Belum ada kandidat lain.")

                        st.divider()
                        kolom_tampil = ['NIP', 'Nama Lengkap', 'Jabatan', 'Career_Level', 'Name_Box_Talent', 'Nilai_Kinerja_Semester', 'Nilai_Assessment_UPAC', 'Skor_Suksesi_Final']
                        event_kandidat = st.dataframe(kandidat_pool[kolom_tampil], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

                        selected_nip_talent = None
                        if len(event_kandidat.selection.rows) > 0:
                            selected_nip_talent = kandidat_pool.iloc[event_kandidat.selection.rows[0]]['NIP']
                        elif st.session_state.get('selected_kandidat_nip') in kandidat_pool['NIP'].values:
                            selected_nip_talent = st.session_state['selected_kandidat_nip']

                        if selected_nip_talent is not None:
                            data_talent = kandidat_pool[kandidat_pool['NIP'] == selected_nip_talent].iloc[0]
                            
                            st.divider()
                            st.subheader(f"🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent['Nama Lengkap']}")
                            
                            col_profil, col_radar = st.columns([1.2, 1.5]) 
                            with col_profil:
                                st.markdown(f"**NIP:** `{data_talent['NIP']}`")
                                st.markdown(f"**Jabatan Saat Ini:** {data_talent['Jabatan']} ({data_talent['Company Name']})")
                                st.markdown(f"**Grade:** {data_talent['Person Grade']} | **Status Kapasitas:** {data_talent['Career_Level']}")
                                
                                bt = data_talent['Name_Box_Talent'] if pd.notna(data_talent['Name_Box_Talent']) else "Data Belum Tersedia"
                                st.info(f"📊 **9-Box Talent Placement:** {bt}")
                                
                                dimensi_31 = ['CEE', 'BAC', 'DCM', 'DOR', 'PNO', 'BTR', 'COL', 'BPA', 'INF', 'ADA', 'CLE', 'COC', 'CIM', 'EXE', 'FCH', 'IOT', 'ABS', 'NUM', 'VER', 'I', 'F', 'A', 'C', 'E', 'S', 'COM', 'TMW', 'SEF', 'INI', 'DEC', 'SER']
                                skor_31_dimensi = int(data_talent[dimensi_31].fillna(0).sum())
                                
                                st.success(f"⭐ **Total Assessment Psikologis (31 Dimensi):** {skor_31_dimensi}")
                                st.success(f"⭐ **Skor Suksesi Final:** {int(data_talent['Skor_Suksesi_Final'])}")
                                st.caption(f"*(Gabungan dari **Kinerja Semester:** {data_talent['Nilai_Kinerja_Semester']} + **Assessment UPAC:** {data_talent['Nilai_Assessment_UPAC']})*")
                                
                                # --- [PEMBARUAN] NARASI ANALISIS KELAYAKAN PROMOSI ---
                                st.markdown("---")
                                st.markdown("💡 **Analisis Kelayakan Promosi:**")
                                alasan_layak = f"Berdasarkan **Perdir PT PLN No. 0050/2023**, posisi kandidat saat ini sebagai **{data_talent['Career_Level']}** dengan **Person Grade {data_talent['Person Grade']}** memenuhi syarat *eligibility* mutlak untuk menduduki posisi **{target_career_level}**. Selain memenuhi kriteria kepatuhan administratif, kandidat sangat direkomendasikan karena masuk dalam kategori Talenta Unggul (**{bt}**) dan memiliki akumulasi skor Kinerja & Assessment yang sangat memuaskan (**{int(data_talent['Skor_Suksesi_Final'])}**)."
                                st.markdown(alasan_layak)
                            
                            with col_radar:
                                kompetensi = {
                                    'CEE (Customer Focus)': data_talent['CEE'] if pd.notna(data_talent['CEE']) else 0,
                                    'DCM (Decision Making)': data_talent['DCM'] if pd.notna(data_talent['DCM']) else 0,
                                    'COM (Communication)': data_talent['COM'] if pd.notna(data_talent['COM']) else 0,
                                    'BAC (Business Acumen)': data_talent['BAC'] if pd.notna(data_talent['BAC']) else 0,
                                    'DOR (Drive for Result)': data_talent['DOR'] if pd.notna(data_talent['DOR']) else 0,
                                    'INI (Initiative)': data_talent['INI'] if pd.notna(data_talent['INI']) else 0,
                                    'DEC (Decisiveness)': data_talent['DEC'] if pd.notna(data_talent['DEC']) else 0,
                                    'SEF (Self Confidence)': data_talent['SEF'] if pd.notna(data_talent['SEF']) else 0
                                }
                                
                                if sum(kompetensi.values()) == 0:
                                    st.warning("Belum ada data nilai assessment psikologis untuk kandidat ini.")
                                else:
                                    df_radar = pd.DataFrame(dict(skor=list(kompetensi.values()), parameter=list(kompetensi.keys())))
                                    fig_radar = px.line_polar(df_radar, r='skor', theta='parameter', line_close=True, range_r=[0, 10])
                                    fig_radar.update_traces(fill='toself', line_color='#00A2E9')
                                    st.plotly_chart(fig_radar, use_container_width=True)
                                    
                            # --- FORMAT TABEL RIWAYAT JABATAN ---
                            st.divider()
                            st.subheader("📜 Riwayat Perjalanan Karier")
                            
                            nip_col = 'NIP' if 'NIP' in riwayat_jabatan.columns else 'nip'
                            df_riwayat_kandidat = riwayat_jabatan[riwayat_jabatan[nip_col] == data_talent['NIP']].copy()
                            
                            if not df_riwayat_kandidat.empty:
                                if 'start_date' in df_riwayat_kandidat.columns:
                                    df_riwayat_kandidat['start_date_dt'] = pd.to_datetime(df_riwayat_kandidat['start_date'], errors='coerce')
                                if 'end_date' in df_riwayat_kandidat.columns:
                                    df_riwayat_kandidat['end_date_dt'] = pd.to_datetime(df_riwayat_kandidat['end_date'], errors='coerce')
                                    
                                sekarang = pd.to_datetime('today')
                                def hitung_durasi(row):
                                    start = row.get('start_date_dt', pd.NaT)
                                    end = row.get('end_date_dt', sekarang) if pd.notna(row.get('end_date_dt')) else sekarang
                                    if pd.isna(start): return "-"
                                    delta = end - start
                                    tahun = delta.days // 365
                                    bulan = (delta.days % 365) // 30
                                    if tahun > 0: return f"{tahun} Thn {bulan} Bln"
                                    return f"{bulan} Bln"
                                    
                                df_riwayat_kandidat['Durasi'] = df_riwayat_kandidat.apply(hitung_durasi, axis=1)
                                
                                def potong_org(org_val):
                                    if pd.isna(org_val): return "-"
                                    parts = [p.strip() for p in str(org_val).split('-')]
                                    return " - ".join(parts[:3])
                                
                                if 'organisasi' in df_riwayat_kandidat.columns:
                                    df_riwayat_kandidat['Organisasi (Max Level 3)'] = df_riwayat_kandidat['organisasi'].apply(potong_org)
                                    
                                df_riwayat_kandidat['Mulai Menjabat'] = df_riwayat_kandidat['start_date_dt'].dt.strftime('%d %b %Y').fillna('-') if 'start_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('start_date', '-')
                                df_riwayat_kandidat['Akhir Menjabat'] = df_riwayat_kandidat['end_date_dt'].dt.strftime('%d %b %Y').fillna('Sekarang') if 'end_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('end_date', '-')
                                
                                if 'end_date_dt' in df_riwayat_kandidat.columns:
                                    df_riwayat_kandidat = df_riwayat_kandidat.sort_values(by='end_date_dt', ascending=False, na_position='first')
                                    
                                kolom_tersedia = df_riwayat_kandidat.columns.tolist()
                                kolom_final = [nip_col, 'Mulai Menjabat', 'Akhir Menjabat', 'Durasi']
                                
                                if 'jabatan' in kolom_tersedia: kolom_final.append('jabatan')
                                if 'jenis jabatan' in kolom_tersedia: kolom_final.append('jenis jabatan')
                                if 'jenjang jabatan' in kolom_tersedia: kolom_final.append('jenjang jabatan')
                                if 'Organisasi (Max Level 3)' in df_riwayat_kandidat.columns: kolom_final.append('Organisasi (Max Level 3)')
                                
                                df_tampil = df_riwayat_kandidat[kolom_final].rename(columns={
                                    nip_col: 'NIP',
                                    'jabatan': 'Jabatan',
                                    'jenis jabatan': 'Jenis Jabatan',
                                    'jenjang jabatan': 'Jenjang Jabatan'
                                })
                                
                                st.dataframe(df_tampil, use_container_width=True, hide_index=True)
                            else:
                                st.info("Tidak ada data riwayat jabatan yang ditemukan untuk kandidat ini.")
                                
                    else:
                        st.error("⚠️ Kandidat yang tersedia tidak memenuhi syarat pola Jenjang Karir / Person Grade yang ditetapkan pada dokumen Peraturan Pelaksana.")
                else:
                    st.warning("Tidak ditemukan kandidat dengan Box Talent 'Promotable/Solid' yang satu dahan profesi dan berstatus Available.")

    # =========================================================================
    # TAB 3: ANALITIK KPI UNIT INDUK VS KPI INDIVIDU
    # =========================================================================
    with tab3:
        st.header("📈 Analitik Korelasi: KPI Unit vs KPI Individu")
        st.write("Modul ini membandingkan distribusi nilai kinerja pegawai secara individu terhadap tren pencapaian operasional unit kerjanya.")
        
        df_kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
        df_kinerja_peg = df_kinerja_latest.merge(pegawai[['NIP', 'Nama Lengkap', 'Company Name', 'Business Area', 'Jabatan']], on='NIP', how='inner')
        
        list_ui_kpi = ["-- Pilih Unit Induk --"] + list(df_kinerja_peg['Company Name'].dropna().unique())

        # Bypass otomatis: jika filter unit global (sidebar) aktif, langsung arahkan
        # selectbox ke unit tersebut sehingga grafik KPI langsung tampil tanpa klik ganda.
        default_index_kpi = 0
        if selected_unit_filter != "-- Semua Unit --":
            match_unit_kpi = [u for u in list_ui_kpi if str(u).upper() == selected_unit_filter.upper()]
            if match_unit_kpi:
                default_index_kpi = list_ui_kpi.index(match_unit_kpi[0])
                st.caption(f"🔒 Filter global aktif — otomatis menampilkan analisis KPI untuk **{selected_unit_filter}**.")
            else:
                st.warning(f"Unit **{selected_unit_filter}** dari filter global belum memiliki data KPI di modul ini.")

        selected_ui_kpi = st.selectbox("👉 Pilih Unit Induk untuk Analisis KPI:", list_ui_kpi, index=default_index_kpi)
        
        if selected_ui_kpi != "-- Pilih Unit Induk --":
            df_kpi_ui = df_kinerja_peg[df_kinerja_peg['Company Name'] == selected_ui_kpi].copy()
            avg_kpi_individu = df_kpi_ui['Nilai_Kinerja_Semester'].mean()
            
            st.divider()
            colA, colB = st.columns(2)
            
            with colA:
                st.subheader("Distribusi KPI Individu (Pegawai)")
                st.metric(f"Rata-rata Nilai Kinerja Individu", f"{avg_kpi_individu:.2f}")
                
                df_kpi_ui['Rentang Kinerja'] = pd.cut(df_kpi_ui['Nilai_Kinerja_Semester'], bins=15)
                df_kpi_ui['Label Rentang'] = df_kpi_ui['Rentang Kinerja'].apply(lambda x: f"{int(x.left)} - {int(x.right)}" if pd.notna(x) else "Unknown").astype(str)
                
                df_bar = df_kpi_ui.groupby('Label Rentang').size().reset_index(name='Jumlah Pegawai')
                
                df_bar['Sort_Key'] = df_bar['Label Rentang'].apply(lambda x: int(x.split(' - ')[0]) if x != "Unknown" else 0)
                df_bar = df_bar.sort_values('Sort_Key')
                
                df_bar['Bin_Mid'] = df_bar['Label Rentang'].apply(lambda x: (int(x.split(' - ')[0]) + int(x.split(' - ')[1])) / 2 if x != "Unknown" else 0).astype(float)
                df_bar['Kategori'] = np.where(df_bar['Bin_Mid'] >= avg_kpi_individu, 'Di Atas Rata-rata (Hijau)', 'Di Bawah Rata-rata (Merah)')

                fig_dist = px.bar(
                    df_bar, x='Label Rentang', y='Jumlah Pegawai', 
                    title=f"Sebaran Nilai Kinerja di {selected_ui_kpi} (Rata-rata: {avg_kpi_individu:.2f})",
                    color='Kategori',
                    color_discrete_map={'Di Atas Rata-rata (Hijau)': '#22C55E', 'Di Bawah Rata-rata (Merah)': '#EF4444'}
                )
                fig_dist.update_xaxes(categoryorder='array', categoryarray=df_bar['Label Rentang'].tolist())
                fig_dist.update_layout(legend_title_text='')

                event_hist = st.plotly_chart(fig_dist, use_container_width=True, on_select="rerun", selection_mode="points")
                
            with colB:
                st.subheader("Daftar Pegawai per Rentang KPI")
                if len(event_hist.selection.points) > 0:
                    clicked_bin = event_hist.selection.points[0]["x"]
                    st.success(f"📌 Menampilkan daftar pegawai pada rentang nilai kinerja: **{clicked_bin}**")
                    df_clicked = df_kpi_ui[df_kpi_ui['Label Rentang'] == clicked_bin].sort_values('Nilai_Kinerja_Semester', ascending=False)
                    st.dataframe(df_clicked[['NIP', 'Nama Lengkap', 'Jabatan', 'Business Area', 'Nilai_Kinerja_Semester']], use_container_width=True, hide_index=True)
                else:
                    st.info("💡 **Tips Interaktif:** Klik salah satu batang pada grafik di sebelah kiri untuk melihat rincian nama pegawai pada rentang nilai tersebut.")

            st.divider()
            st.subheader(f"🏆 Top Performers (KPI Individu Tertinggi di {selected_ui_kpi})")
            top_performers = df_kpi_ui.nlargest(10, 'Nilai_Kinerja_Semester')
            st.dataframe(top_performers[['NIP', 'Nama Lengkap', 'Jabatan', 'Business Area', 'Nilai_Kinerja_Semester']], use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("⚙️ Performa Operasional Unit (Simprod)")
            
            if simprod.empty:
                st.info("Data Simprod belum terintegrasi untuk disandingkan.")
            else:
                ui_terpilih_upper = selected_ui_kpi.upper()
                df_hcbp_filtered = hcbp[hcbp['UNIT INDUK'].str.upper() == ui_terpilih_upper]
                
                if not df_hcbp_filtered.empty:
                    list_unit_ops = sorted(df_hcbp_filtered['UNIT PELAKSANA'].dropna().unique())
                else:
                    st.warning("Nama Unit Induk ini belum terpetakan di dokumen Master HCBP.")
                    list_unit_ops = ["-- Cari Manual --"] + sorted(simprod['unit_name'].dropna().unique())
                
                unit_operasional = st.selectbox(f"Pilih Unit Pelaksana di {selected_ui_kpi}:", list_unit_ops)
                
                if unit_operasional and unit_operasional != "-- Cari Manual --":
                    core_up_name = re.sub(r'^(UP3|UP2\w|ULP|UPT|UPDK|UPK|UID|UIK|UIP\w*|UIT|UIW|AREA|SEKTOR|TRAGI|UNIT PELAKSANA[\w\s]*)\s+', '', unit_operasional, flags=re.IGNORECASE).strip()
                    
                    df_simprod_unit = simprod[
                        simprod['unit_name'].str.contains(core_up_name, case=False, na=False)
                    ].sort_values(['periode_year', 'periode_part']).copy()
                    
                    df_simprod_unit['Periode'] = df_simprod_unit['periode_year'].astype(str) + " - S" + df_simprod_unit['periode_part'].astype(str)
                    
                    if not df_simprod_unit.empty:
                        nama_simprod_terdeteksi = " & ".join(df_simprod_unit['unit_name'].unique())
                        st.caption(f"🔗 *Data terhubung dengan catatan Simprod:* **{nama_simprod_terdeteksi}**")
                        
                        potensi_kpi = ['oee_pembangkit', 'force_outage', 'saidi', 'pendapatan', 'trafo_loss', 'kms', 'mva', 'auxilary_power']
                        kpi_tersedia = [col for col in potensi_kpi if col in df_simprod_unit.columns and not df_simprod_unit[col].isna().all()]
                        
                        if kpi_tersedia:
                            default_kpi = kpi_tersedia[:2]
                            selected_kpi = st.multiselect("Pilih Indikator Operasional:", kpi_tersedia, default=default_kpi)
                            
                            if selected_kpi:
                                fig_line = px.line(
                                    df_simprod_unit, 
                                    x='Periode', 
                                    y=selected_kpi, 
                                    markers=True, 
                                    title=f"Tren Performa: {unit_operasional}"
                                )
                                fig_line.update_layout(yaxis_title="Nilai Metrik", legend_title="Indikator")
                                st.plotly_chart(fig_line, use_container_width=True)
                            else:
                                st.info("Pilih setidaknya satu indikator operasional pada kotak di atas.")
                        else:
                            st.warning("Tidak ada riwayat nilai metrik KPI yang terekam untuk unit ini di database Simprod.")
                    else:
                        st.info(f"Belum ada data operasional yang ditarik untuk {unit_operasional} di dalam file Simprod saat ini.")
