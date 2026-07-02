import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Konfigurasi Halaman Utama
st.set_page_config(page_title="HR Analytics Dashboard - PLN", page_icon="⚡", layout="wide")

@st.cache_data
def load_and_process_hr_data():
    # 1. Load Dataset Utama
    pegawai = pd.read_csv('Synthetic_Data_Pegawai_Patched.csv', low_memory=False)
    kinerja = pd.read_csv('Synthetic_Data_Kinerja.csv')
    assessment = pd.read_csv('Synthetic_Data_Hasil_Assessment_Psikologis_Potensi.csv')
    aps = pd.read_csv('Synthetic_APS_Data.csv')
    
    try:
        simprod = pd.read_csv('Simprod_Flattened.csv')
    except:
        simprod = pd.DataFrame()

    # =========================================================================
    # CATATAN HR 1: Eksklusi pegawai > 56 tahun (Sudah Pensiun)
    # =========================================================================
    pegawai = pegawai[pegawai['Umur Tahun'] <= 56].copy()

    # 2. Hitung Parameter Durasi Jabatan
    pegawai['Start Date Jabatan'] = pd.to_datetime(pegawai['Start Date Jabatan'], errors='coerce')
    tanggal_evaluasi = pd.to_datetime('today')
    pegawai['Lama_Menjabat_Tahun'] = (tanggal_evaluasi - pegawai['Start Date Jabatan']).dt.days / 365.25

    # =========================================================================
    # CATATAN HR 2: Eksklusi Officer, Technician, Tugas Belajar dari SLA Masa Jabatan
    # =========================================================================
    def hitung_status_ews_eksekutif(row):
        w = []
        # Cek Kriteria Pensiun (Berlaku untuk semua level yang masih aktif)
        if pd.notna(row['Umur Tahun']) and row['Umur Tahun'] >= 55:
            w.append("Mendekati Pensiun")
            
        # Cek Kata Kunci Level Staff
        jabatan_teks = str(row['Jabatan']).lower()
        is_staff = any(keyword in jabatan_teks for keyword in ['officer', 'technician', 'tugas belajar'])
        
        # SLA hanya dihitung jika BUKAN staff (Level Manajerial/Struktural/Eksekutif)
        if not is_staff:
            if pd.notna(row['Lama_Menjabat_Tahun']) and row['Lama_Menjabat_Tahun'] >= 4.0:
                w.append("Menjabat > 4 Tahun")
                
        return " | ".join(w) if w else "Aman"
    
    pegawai['Status_EWS'] = pegawai.apply(hitung_status_ews_eksekutif, axis=1)

    # 3. Sinkronisasi Data Profiler & Status Ketersediaan (Pencegah Double Offer)
    kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    assessment_latest = assessment.sort_values('Tanggal_Assessment_UPAC').drop_duplicates('NIP', keep='last')

    profiler = pegawai[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Business Area', 'Personal Sub Area', 'Kode dan Dahan Profesi']].copy()
    profiler = profiler.merge(kinerja_latest[['NIP', 'Name_Box_Talent']], on='NIP', how='left')
    profiler = profiler.merge(assessment_latest[['NIP', 'CEE', 'DCM', 'COM']], on='NIP', how='left')

    # Status Ketersediaan Berdasarkan Data Proses APS/Mutasi yang sedang berjalan
    nips_dalam_aps = aps['NIP'].unique()
    profiler['Status_Ketersediaan'] = np.where(profiler['NIP'].isin(nips_dalam_aps), 'Not Available (Dalam Proses Mutasi/APS)', 'Available')

    return pegawai, profiler, aps, simprod

# Eksekusi Load Data dengan Spinner Animasi
with st.spinner("Sinkronisasi Database HR PLN... Mohon Tunggu."):
    pegawai, profiler, aps, simprod = load_and_process_hr_data()

st.title("⚡ Tower 5 - Perencanaan Suksesi Analitik")
st.markdown("Dashboard Monitoring Suksesi Jabatan Struktural PLN")

# Inisialisasi Tab Aplikasi
tab1, tab2, tab3 = st.tabs(["🚨 Tab 1: EWS Pensiun & Masa Jabatan", "🎯 Tab 2: Suksesi Jabatan & Profiler", "📈 Tab 3: Analitik Mobilitas vs KPI"])

# =========================================================================
# TAB 1: DRILL-DOWN EARLY WARNING SYSTEM (EWS)
# =========================================================================
with tab1:
    st.header("🚨 Peta Kerawanan Suksesi Jabatan (EWS)")
    st.write("💡 **Tips Interaktif:** Klik pada salah satu baris tabel di bawah untuk menelusuri data secara mendalam (*Deep Dive*).")
    
    # Filter hanya yang terkena alert EWS
    df_ews_aktif = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()
    
    # --- LEVEL 1: Tampilan Unit Induk ---
    st.subheader("📊 Level 1: Jumlah Kasus EWS per Unit Induk")
    summary_unit_induk = df_ews_aktif.groupby('Company Name').size().reset_index(name='Jumlah Pegawai Alert')
    summary_unit_induk = summary_unit_induk.sort_values(by='Jumlah Pegawai Alert', ascending=False)
    
    # Tabel interaktif (Klik untuk memilih)
    event_ui = st.dataframe(
        summary_unit_induk, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row"
    )
    
    # Jika ada baris Unit Induk yang diklik
    if len(event_ui.selection.rows) > 0:
        idx_ui = event_ui.selection.rows[0]
        selected_ui = summary_unit_induk.iloc[idx_ui]['Company Name']
        
        # --- LEVEL 2: Tampilan Unit Pelaksana & Layanan ---
        st.divider()
        st.subheader(f"🏢 Level 2: Detail Sebaran di {selected_ui}")
        df_filtered_ui = df_ews_aktif[df_ews_aktif['Company Name'] == selected_ui]
        summary_pelaksana = df_filtered_ui.groupby(['Business Area', 'Personal Sub Area']).size().reset_index(name='Jumlah Kasus')
        summary_pelaksana = summary_pelaksana.sort_values(by='Jumlah Kasus', ascending=False)
        
        # Tabel interaktif kedua
        event_up = st.dataframe(
            summary_pelaksana, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        # Jika ada baris Unit Pelaksana yang diklik
        if len(event_up.selection.rows) > 0:
            idx_up = event_up.selection.rows[0]
            selected_up = summary_pelaksana.iloc[idx_up]['Business Area']
            
            # --- LEVEL 3: Detail Individu Kena EWS ---
            st.divider()
            st.subheader(f"📋 Level 3: Daftar Personil Masuk Radar EWS di {selected_up}")
            
            df_final_karyawan = df_filtered_ui[df_filtered_ui['Business Area'] == selected_up].copy()
            df_final_karyawan['Lama_Menjabat_Tahun'] = df_final_karyawan['Lama_Menjabat_Tahun'].round(1)
            kolom_final = ['NIP', 'Nama Lengkap', 'Jabatan', 'Lama_Menjabat_Tahun', 'Umur Tahun', 'Status_EWS']
            
            st.dataframe(df_final_karyawan[kolom_final], use_container_width=True, hide_index=True)

# =========================================================================
# TAB 2: SUKSESI JABATAN KOSONG & PROFILER TALENT
# =========================================================================
with tab2:
    st.header("🎯 Perencanaan Pengisian Jabatan Kosong (Suksesi)")
    st.write("💡 **Tips Interaktif:** Klik pada baris tabel untuk menelusuri posisi kosong hingga memunculkan rekomendasi kandidat.")

    # Ambil data EWS yang butuh suksesi
    df_jabatan_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()

    # --- FILTERING LEVEL STAFF ---
    # Eksklusi jabatan non-struktural secara tegas dari Tab 2
    keywords_staff = ['officer', 'technician', 'tugas belajar']
    df_jabatan_kosong = df_jabatan_kosong[
        ~df_jabatan_kosong['Jabatan'].str.lower().str.contains('|'.join(keywords_staff), na=False)
    ]

    # --- LEVEL 1: Sebaran Jabatan Kosong per Unit Induk ---
    st.subheader("📊 Level 1: Proyeksi Lowongan Jabatan Struktural per Unit Induk")
    summary_vacancy_ui = df_jabatan_kosong.groupby('Company Name').size().reset_index(name='Total Posisi Butuh Suksesi')
    summary_vacancy_ui = summary_vacancy_ui.sort_values(by='Total Posisi Butuh Suksesi', ascending=False)
    
    event_vac_ui = st.dataframe(
        summary_vacancy_ui, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row"
    )

    # Jika Unit Induk diklik
    if len(event_vac_ui.selection.rows) > 0:
        idx_vac_ui = event_vac_ui.selection.rows[0]
        selected_vac_ui = summary_vacancy_ui.iloc[idx_vac_ui]['Company Name']
        
        # --- LEVEL 2: Detail Jabatan Kosong di Unit Pelaksana/Layanan ---
        st.divider()
        st.subheader(f"🔍 Level 2: Detail Posisi Jabatan Struktural Terbuka di {selected_vac_ui}")
        df_filtered_vac = df_jabatan_kosong[df_jabatan_kosong['Company Name'] == selected_vac_ui]
        
        # Grouping dengan memasukkan Status_EWS sebagai Alasan
        summary_vac_detail = df_filtered_vac.groupby(
            ['Business Area', 'Personal Sub Area', 'Jabatan', 'Status_EWS', 'Kode dan Dahan Profesi', 'NIP']
        ).size().reset_index(name='Kasus')
        
        # Rename kolom agar lebih mudah dipahami oleh Business User
        summary_vac_detail.rename(columns={'Status_EWS': 'Alasan Kebutuhan Suksesi'}, inplace=True)
        
        event_vac_up = st.dataframe(
            summary_vac_detail[['Business Area', 'Personal Sub Area', 'Jabatan', 'Alasan Kebutuhan Suksesi']], 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-row"
        )

        # Jika Jabatan Spesifik diklik
        if len(event_vac_up.selection.rows) > 0:
            idx_vac_up = event_vac_up.selection.rows[0]
            dahan_profesi_target = summary_vac_detail.iloc[idx_vac_up]['Kode dan Dahan Profesi']
            nip_pejabat_saat_ini = summary_vac_detail.iloc[idx_vac_up]['NIP']
            
            # --- LEVEL 3: Rekomendasi Daftar Calon Kandidat Terpilih ---
            st.divider()
            st.subheader(f"👥 Level 3: Kandidat Suksesor (Kesesuaian Dahan: {dahan_profesi_target})")
            
            kandidat_pool = profiler[
                (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
                (profiler['NIP'] != nip_pejabat_saat_ini)
            ].copy()
            
            if not kandidat_pool.empty:
                event_kandidat = st.dataframe(
                    kandidat_pool[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Name_Box_Talent', 'Status_Ketersediaan']], 
                    use_container_width=True, 
                    hide_index=True,
                    on_select="rerun", 
                    selection_mode="single-row"
                )
                
                # --- LEVEL 4: Review Profil & Radar Kompetensi Kandidat ---
                if len(event_kandidat.selection.rows) > 0:
                    idx_kandidat = event_kandidat.selection.rows[0]
                    data_talent = kandidat_pool.iloc[idx_kandidat]
                    
                    st.divider()
                    st.subheader(f"🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent['Nama Lengkap']}")
                    
                    col_profil, col_radar = st.columns([1, 1])
                    with col_profil:
                        st.markdown(f"**NIP:** `{data_talent['NIP']}`")
                        st.markdown(f"**Asal Unit Induk:** {data_talent['Company Name']}")
                        st.markdown(f"**Jabatan Saat Ini:** {data_talent['Jabatan']}")
                        
                        bt = data_talent['Name_Box_Talent'] if pd.notna(data_talent['Name_Box_Talent']) else "Data Belum Tersedia"
                        st.info(f"📊 **9-Box Talent Placement:** {bt}")
                        
                        if "Not Available" in data_talent['Status_Ketersediaan']:
                            st.error(f"⚠️ **Status Suksesi:** {data_talent['Status_Ketersediaan']}")
                        else:
                            st.success(f"✅ **Status Suksesi:** {data_talent['Status_Ketersediaan']} (Bisa Diajukan)")
                    
                    with col_radar:
                        cee = data_talent['CEE'] if pd.notna(data_talent['CEE']) else 0
                        dcm = data_talent['DCM'] if pd.notna(data_talent['DCM']) else 0
                        com = data_talent['COM'] if pd.notna(data_talent['COM']) else 0
                        
                        if cee == 0 and dcm == 0 and com == 0:
                            st.warning("Belum ada data nilai psikologis (CEE, DCM, COM).")
                        else:
                            df_radar = pd.DataFrame(dict(
                                skor=[cee, dcm, com],
                                parameter=['CEE (Customer Focus)', 'DCM (Decision Making)', 'COM (Communication)']
                            ))
                            fig_radar = px.line_polar(df_radar, r='skor', theta='parameter', line_close=True, range_r=[0, 10])
                            fig_radar.update_traces(fill='toself', line_color='#00A2E9')
                            st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("Tidak ada kandidat dengan dahan profesi sejenis yang berstatus Available.")

# =========================================================================
# TAB 3: ANALITIK MOBILITAS VS KPI
# =========================================================================
with tab3:
    st.header("📈 Evaluasi Mobilitas (APS) terhadap KPI Unit")
    st.write("Modul integrasi data mutasi pegawai (APS) dengan performa unit operasional (Simprod).")
    if simprod.empty:
        st.info("Data Simprod belum terhubung secara sempurna. Pastikan file Simprod_Flattened.csv tersedia.")
    else:
        st.success("Data Simprod Terdeteksi Aktif. Silakan hubungkan parameter visualisasi lanjutan.")
