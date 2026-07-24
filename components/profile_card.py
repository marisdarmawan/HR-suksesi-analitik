import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Import konfigurasi dan aturan bisnis
from config import DIMENSI_31, KEYWORDS_STAFF_REGEX, ELIGIBLE_TALENT_BOX
from utils.business_logic import get_official_category, is_eligible
from utils.preprocessor import prep_riwayat_jabatan

# ==========================================================
# 1. KOMPONEN UI: PROFIL EKSEKUTIF & RADAR CHART
# ==========================================================
def render_profil_eksekutif(data_talent, target_career_level=None):
    """
    Me-render kartu profil kandidat eksekutif, mencakup skor 31 Dimensi
    dan Plotly Radar Chart untuk 8 Core Competencies.
    """
    col_profil, col_radar = st.columns([1.2, 1.5]) 
    
    with col_profil:
        st.markdown(f"**Nama Lengkap:** {data_talent['Nama Lengkap']}")
        st.markdown(f"**NIP:** `{data_talent['NIP']}`")
        st.markdown(f"**Jabatan Saat Ini:** {data_talent['Jabatan']} ({data_talent['Company Name']})")
        st.markdown(f"**Grade:** {data_talent['Person Grade']} | **Status Kapasitas:** {data_talent['Career_Level']}")
        
        bt = data_talent['Name_Box_Talent'] if pd.notna(data_talent['Name_Box_Talent']) else "Data Belum Tersedia"
        st.info(f"📊 **9-Box Talent Placement:** {bt}")
        
        # Hitung skor total 31 Dimensi
        skor_31_dimensi = int(data_talent[DIMENSI_31].fillna(0).sum())
        
        # Ambil nilai agregat
        nks = data_talent.get('Nilai_Kinerja_Semester', 0)
        if pd.isna(nks): nks = 0
        nau = data_talent.get('Nilai_Assessment_UPAC', 0)
        if pd.isna(nau): nau = 0
        skor_final = int(nks + nau)
        
        st.success(f"⭐ **Total Assessment Psikologis (31 Dimensi):** {skor_31_dimensi}")
        st.success(f"⭐ **Skor Suksesi Final:** {skor_final}")
        st.caption(f"*(Gabungan dari **Kinerja Semester:** {nks} + **Assessment UPAC:** {nau})*")
        
        # Tampilkan narasi analisis jika ini diakses dari modul suksesi (memiliki target jabatan)
        if target_career_level:
            st.markdown("---")
            st.markdown("💡 **Analisis Kelayakan Promosi:**")
            alasan_layak = f"Berdasarkan **Perdir PT PLN No. 0050/2023**, posisi kandidat saat ini sebagai **{data_talent['Career_Level']}** dengan **Person Grade {data_talent['Person Grade']}** memenuhi syarat *eligibility* mutlak untuk menduduki posisi **{target_career_level}**. Selain memenuhi kriteria kepatuhan administratif, kandidat sangat direkomendasikan karena masuk dalam kategori Talenta Unggul (**{bt}**) dan memiliki akumulasi skor Kinerja & Assessment yang sangat memuaskan (**{skor_final}**)."
            st.markdown(alasan_layak)
    
    with col_radar:
        # Menyiapkan 8 Core Competencies untuk grafik radar
        kompetensi = {
            'CEE (Customer Focus)': data_talent.get('CEE', 0) if pd.notna(data_talent.get('CEE', 0)) else 0,
            'DCM (Decision Making)': data_talent.get('DCM', 0) if pd.notna(data_talent.get('DCM', 0)) else 0,
            'COM (Communication)': data_talent.get('COM', 0) if pd.notna(data_talent.get('COM', 0)) else 0,
            'BAC (Business Acumen)': data_talent.get('BAC', 0) if pd.notna(data_talent.get('BAC', 0)) else 0,
            'DOR (Drive for Result)': data_talent.get('DOR', 0) if pd.notna(data_talent.get('DOR', 0)) else 0,
            'INI (Initiative)': data_talent.get('INI', 0) if pd.notna(data_talent.get('INI', 0)) else 0,
            'DEC (Decisiveness)': data_talent.get('DEC', 0) if pd.notna(data_talent.get('DEC', 0)) else 0,
            'SEF (Self Confidence)': data_talent.get('SEF', 0) if pd.notna(data_talent.get('SEF', 0)) else 0
        }
        
        if sum(kompetensi.values()) == 0:
            st.warning("Belum ada data nilai assessment psikologis untuk kandidat ini.")
        else:
            df_radar = pd.DataFrame(dict(skor=list(kompetensi.values()), parameter=list(kompetensi.keys())))
            fig_radar = px.line_polar(df_radar, r='skor', theta='parameter', line_close=True, range_r=[0, 10])
            fig_radar.update_traces(fill='toself', line_color='#00A2E9')
            st.plotly_chart(fig_radar, use_container_width=True)


# ==========================================================
# 2. KOMPONEN UI: RIWAYAT JABATAN
# ==========================================================
def render_riwayat_jabatan(db_riwayat, nip_kandidat):
    """
    Me-render tabel riwayat perjalanan karier dengan memanggil 
    data yang telah di-preprocess.
    """
    st.divider()
    st.subheader("📜 Riwayat Perjalanan Karier")
    
    # Pemrosesan tanggal dan durasi dilakukan di utils/preprocessor.py
    df_tampil = prep_riwayat_jabatan(db_riwayat, nip_kandidat)
    
    if not df_tampil.empty:
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada data riwayat jabatan yang ditemukan untuk kandidat ini.")


# ==========================================================
# 3. LOGIKA PENCARIAN GLOBAL
# ==========================================================
def render_search_results(search_query, selected_unit, db):
    """
    Menangani kueri pencarian dari sidebar dan menampilkan hasil 
    berdasarkan Nama Pegawai atau Posisi Jabatan.
    """
    profiler = db['profiler']
    pegawai = db['pegawai']
    riwayat_jabatan = db['riwayat']
    
    # Terapkan filter unit jika aktif
    if selected_unit != "-- Semua Unit --":
        profiler_f = profiler[profiler['Company Name'].str.upper() == selected_unit.upper()]
        pegawai_f = pegawai[pegawai['Company Name'].str.upper() == selected_unit.upper()]
    else:
        profiler_f = profiler
        pegawai_f = pegawai

    # Cari kecocokan substring (case-insensitive)
    pegawai_matched = profiler_f[profiler_f['Nama Lengkap'].str.lower().str.contains(search_query.lower(), na=False)]
    jabatan_matched = pegawai_f[pegawai_f['Jabatan'].str.lower().str.contains(search_query.lower(), na=False)]
    
    # ------------------------------------------------------
    # SKENARIO A: PENCARIAN NAMA PEGAWAI
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
            
            # Panggil komponen UI yang dapat digunakan ulang
            render_profil_eksekutif(row)
            render_riwayat_jabatan(riwayat_jabatan, row['NIP'])
            
            # --- CEK REKOMENDASI PROMOSI ---
            if row['Status_Ketersediaan'] == 'Available' and row['Name_Box_Talent'] in ELIGIBLE_TALENT_BOX:
                st.divider()
                st.subheader(f"🚀 Rekomendasi Promosi Jabatan")
                st.write(f"Berikut adalah posisi struktural yang saat ini sedang kosong/membutuhkan suksesi dan sesuai dengan kualifikasi jenjang karir **{row['Nama Lengkap']}**:")
                
                df_jab_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()
                df_jab_kosong = df_jab_kosong[~df_jab_kosong['Jabatan'].str.lower().str.contains(KEYWORDS_STAFF_REGEX, regex=True, na=False)]
                
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
                    st.dataframe(pd.DataFrame(layak_list), use_container_width=True, hide_index=True)
                    st.markdown("💡 **Analisis Kelayakan Promosi:**")
                    alasan_layak = f"Berdasarkan **Perdir PT PLN No. 0050/2023**, posisi kandidat saat ini sebagai **{row['Career_Level']}** dengan **Person Grade {row['Person Grade']}** memenuhi syarat *eligibility* mutlak untuk menduduki posisi-posisi di atas. Selain memenuhi kriteria kepatuhan administratif, kandidat direkomendasikan karena masuk dalam kategori Talenta Unggul (**{row['Name_Box_Talent']}**)."
                    st.success(alasan_layak)
                else:
                    st.info("Saat ini tidak ada posisi struktural kosong di dahan profesi yang sama yang sesuai dengan jenjang karir kandidat ini.")

    # ------------------------------------------------------
    # SKENARIO B: PENCARIAN POSISI JABATAN
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
                
                target_career_level = get_official_category(row['Jabatan'], 0, row['Business Area'])
                st.subheader(f"👥 Daftar Calon Suksesor")
                st.caption(f"Target Posisi diidentifikasi sebagai **{target_career_level}**.")
                
                # Saring kandidat (Dahan sama, box talent unggul, available, bukan pejabat saat ini)
                kandidat_pool = profiler[
                    (profiler['Kode dan Dahan Profesi'] == row['Kode dan Dahan Profesi']) & 
                    (profiler['NIP'] != row['NIP']) &
                    (profiler['Name_Box_Talent'].isin(ELIGIBLE_TALENT_BOX)) &
                    (profiler['Status_Ketersediaan'] == 'Available')
                ].copy()
                 
                if not kandidat_pool.empty:
                    # Validasi aturan Perdir
                    kandidat_pool = kandidat_pool[kandidat_pool.apply(lambda x: is_eligible(x['Career_Level'], x['Person Grade'], target_career_level), axis=1)]
                    
                    if not kandidat_pool.empty:
                        kandidat_pool['Nilai_Kinerja_Semester'] = kandidat_pool['Nilai_Kinerja_Semester'].fillna(0)
                        kandidat_pool['Nilai_Assessment_UPAC'] = kandidat_pool['Nilai_Assessment_UPAC'].fillna(0)
                        kandidat_pool['Skor_Suksesi_Final'] = kandidat_pool['Nilai_Kinerja_Semester'] + kandidat_pool['Nilai_Assessment_UPAC']
                        kandidat_pool = kandidat_pool.sort_values(by='Skor_Suksesi_Final', ascending=False)
                        
                        st.write("👉 **Klik kandidat di bawah ini untuk melihat detail (Level 4 & Riwayat Karir):**")
                        kolom_tampil = ['NIP', 'Nama Lengkap', 'Jabatan', 'Career_Level', 'Name_Box_Talent', 'Skor_Suksesi_Final']
                        event_kandidat = st.dataframe(kandidat_pool[kolom_tampil], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="tbl_cand_jab_search")
                        
                        if len(event_kandidat.selection.rows) > 0:
                            data_talent_cand = kandidat_pool.iloc[event_kandidat.selection.rows[0]]
                            st.divider()
                            st.markdown(f"#### 🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent_cand['Nama Lengkap']}")
                            render_profil_eksekutif(data_talent_cand, target_career_level)
                            render_riwayat_jabatan(riwayat_jabatan, data_talent_cand['NIP'])
                    else:
                        st.error("⚠️ Kandidat yang tersedia tidak memenuhi syarat pola Jenjang Karir / Person Grade yang ditetapkan pada dokumen Peraturan Pelaksana.")
                else:
                    st.warning("Tidak ditemukan kandidat dengan Box Talent 'Promotable/Solid' yang satu dahan profesi dan berstatus Available.")
            else:
                st.success("✅ Jabatan ini saat ini terpantau **AMAN** dan belum membutuhkan suksesi mendesak.")
                
    else:
        st.warning("Tidak ditemukan hasil yang cocok dengan pencarian Anda.")