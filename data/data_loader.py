import streamlit as st
import pandas as pd
import numpy as np
import re
from utils.preprocessor import calculate_macro_succession, calculate_career_velocity

# Mengimpor konstanta dan path dari config.py
from config import (
    DATA_FILES, USIA_PENSIUN_MAX, USIA_WARNING_PENSIUN, 
    SLA_JABATAN_TAHUN, KEYWORDS_STAFF_REGEX, DIMENSI_31,
    KEYWORDS_UNAVAILABLE_REGEX
)

# Mengimpor fungsi Perdir PLN dari layer Utils
from utils.business_logic import get_official_category

def hitung_status_ews(row):
    """
    Helper function untuk menentukan status Early Warning System (EWS).
    Dipisahkan agar apply() pandas lebih mudah dibaca.
    """
    w = []
    # Cek batas umur pensiun
    if pd.notna(row['Umur Tahun']) and row['Umur Tahun'] >= USIA_WARNING_PENSIUN: 
        w.append("Mendekati Pensiun")
        
    jabatan_teks = str(row['Jabatan']).lower()
    
    # Deteksi posisi staff menggunakan regex (menghindari false positive)
    is_staff = bool(re.search(KEYWORDS_STAFF_REGEX, jabatan_teks))
    
    # Jika bukan staff, cek masa jabatan
    if not is_staff:
        if pd.notna(row['Lama_Menjabat_Tahun']) and row['Lama_Menjabat_Tahun'] >= SLA_JABATAN_TAHUN: 
            w.append("Over SLA")
            
    return " | ".join(w) if w else "Aman"


@st.cache_data(show_spinner=False)
def get_hr_data():
    """
    Fungsi utama untuk Extract, Transform, Load (ETL).
    Mengembalikan dictionary berisi kumpulan DataFrame HR.
    """
    # ==========================================================
    # 1. EKSTRAKSI (Membaca sumber data)
    # ==========================================================
    pegawai = pd.read_csv(DATA_FILES['pegawai'], low_memory=False)
    kinerja = pd.read_csv(DATA_FILES['kinerja'])
    assessment = pd.read_csv(DATA_FILES['assessment'])
    aps = pd.read_csv(DATA_FILES['aps'])
    riwayat_jabatan = pd.read_csv(DATA_FILES['riwayat']) 
    
    # Menangani error dengan spesifik (menghindari "bare except")
    try:
        hcbp = pd.read_excel(DATA_FILES['hcbp'])
    except FileNotFoundError:
        hcbp = pd.DataFrame(columns=['UNIT INDUK', 'UNIT PELAKSANA'])
    
    try:
        simprod = pd.read_csv(DATA_FILES['simprod'])
    except FileNotFoundError:
        simprod = pd.DataFrame()

    # ==========================================================
    # 2. TRANSFORMASI DASAR (Data Pegawai)
    # ==========================================================
    pegawai = pegawai[pegawai['Umur Tahun'] <= USIA_PENSIUN_MAX].copy()
    pegawai['Start Date Jabatan'] = pd.to_datetime(pegawai['Start Date Jabatan'], errors='coerce')
    
    # Hitung masa jabatan dalam tahun
    pegawai['Lama_Menjabat_Tahun'] = (pd.to_datetime('today') - pegawai['Start Date Jabatan']).dt.days / 365.25
    
    # Terapkan perhitungan EWS
    pegawai['Status_EWS'] = pegawai.apply(hitung_status_ews, axis=1)

    # ==========================================================
    # 3. KONSOLIDASI (Membangun Master Data Profiler)
    # ==========================================================
    # Ambil record terbaru untuk kinerja dan assessment
    kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    assessment_latest = assessment.sort_values('Tanggal_Assessment_UPAC').drop_duplicates('NIP', keep='last')

    # Buat tabel profiler sebagai rujukan utama dashboard
    profiler = pegawai[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Business Area', 'Personal Sub Area', 'Kode dan Dahan Profesi', 'Person Grade']].copy()
    
    # Gabung metrik Kinerja & Box Talent
    profiler = profiler.merge(
        kinerja_latest[['NIP', 'Name_Box_Talent', 'Nilai_Kinerja_Semester', 'Nilai_Assessment_UPAC']], 
        on='NIP', how='left'
    )
    
    # Klasifikasi level jabatan sesuai Perdir PT PLN No. 0050/2023
    profiler['Career_Level'] = profiler.apply(
        lambda x: get_official_category(x['Jabatan'], x['Person Grade'], x['Company Name']), axis=1
    )
    
    # Gabung skor psikologi 31 Dimensi
    kolom_tarik = ['NIP'] + DIMENSI_31
    kolom_tarik = [col for col in kolom_tarik if col in assessment_latest.columns] # Mencegah KeyError
    profiler = profiler.merge(assessment_latest[kolom_tarik], on='NIP', how='left')

    # Hitung ketersediaan pegawai (Filter APS/Tugas Belajar/Cuti)
    nips_dalam_aps = aps['NIP'].unique()
    kondisi_tidak_tersedia = profiler['NIP'].isin(nips_dalam_aps) | profiler['Jabatan'].str.lower().str.contains(KEYWORDS_UNAVAILABLE_REGEX, regex=True, na=False)
    profiler['Status_Ketersediaan'] = np.where(kondisi_tidak_tersedia, 'Not Available (APS / Cuti / Tugas Belajar)', 'Available')

    # ==========================================================
    # 4. LOAD (Packing seluruh hasil)
    # ==========================================================
    db = {
        'pegawai': pegawai,
        'profiler': profiler,
        'aps': aps,
        'simprod': simprod,
        'kinerja': kinerja,
        'hcbp': hcbp,
        'riwayat': riwayat_jabatan
    }
    
    # --- TAMBAHKAN BARIS INI UNTUK CACHE TAB 4 ---
    db['macro_metrics'] = calculate_macro_succession(pegawai, profiler)
    db['career_velocity'] = calculate_career_velocity(riwayat_jabatan)
    # ---------------------------------------------
    
    return db

