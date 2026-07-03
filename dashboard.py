import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Konfigurasi Halaman Utama
st.set_page_config(page_title="HR Analytics Dashboard - PLN", page_icon="⚡", layout="wide")

@st.cache_data
@st.cache_data
def load_and_process_hr_data():
    pegawai = pd.read_csv('Synthetic_Data_Pegawai_Patched.csv', low_memory=False)
    kinerja = pd.read_csv('Synthetic_Data_Kinerja.csv')
    assessment = pd.read_csv('Synthetic_Data_Hasil_Assessment_Psikologis_Potensi.csv')
    aps = pd.read_csv('Synthetic_APS_Data.csv')
    
    # [PEMBARUAN] Load Data Referensi Hierarki Resmi HCBP
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
    tanggal_evaluasi = pd.to_datetime('today')
    pegawai['Lama_Menjabat_Tahun'] = (tanggal_evaluasi - pegawai['Start Date Jabatan']).dt.days / 365.25

    def hitung_status_ews_eksekutif(row):
        w = []
        if pd.notna(row['Umur Tahun']) and row['Umur Tahun'] >= 55: w.append("Mendekati Pensiun")
        jabatan_teks = str(row['Jabatan']).lower()
        is_staff = any(keyword in jabatan_teks for keyword in ['officer', 'technician', 'tugas belajar'])
        if not is_staff:
            if pd.notna(row['Lama_Menjabat_Tahun']) and row['Lama_Menjabat_Tahun'] >= 4.0: w.append("Over SLA")
        return " | ".join(w) if w else "Aman"
    
    pegawai['Status_EWS'] = pegawai.apply(hitung_status_ews_eksekutif, axis=1)

    kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    assessment_latest = assessment.sort_values('Tanggal_Assessment_UPAC').drop_duplicates('NIP', keep='last')

    profiler = pegawai[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Business Area', 'Personal Sub Area', 'Kode dan Dahan Profesi']].copy()
    profiler = profiler.merge(kinerja_latest[['NIP', 'Name_Box_Talent']], on='NIP', how='left')
    profiler = profiler.merge(assessment_latest[['NIP', 'CEE', 'DCM', 'COM', 'BAC', 'DOR', 'INI', 'DEC', 'SEF']], on='NIP', how='left')

    nips_dalam_aps = aps['NIP'].unique()
    profiler['Status_Ketersediaan'] = np.where(profiler['NIP'].isin(nips_dalam_aps), 'Not Available (Dalam Proses Mutasi/APS)', 'Available')

    # [PEMBARUAN] Tambahkan 'hcbp' pada return
    return pegawai, profiler, aps, simprod, kinerja, hcbp

# Panggil fungsi load datanya dengan 6 variabel sekarang
with st.spinner("Sinkronisasi Database HR PLN... Mohon Tunggu."):
    pegawai, profiler, aps, simprod, kinerja, hcbp = load_and_process_hr_data()

st.title("⚡ Tower 5 - Perencanaan Suksesi Analitik")
st.markdown("Dashboard Monitoring Suksesi Jabatan Struktural PLN")

# Inisialisasi Tab Aplikasi
tab1, tab2, tab3 = st.tabs(["🚨 Tab 1: EWS Pensiun & Masa Jabatan", "🎯 Tab 2: Suksesi Jabatan & Profiler", "📈 Tab 3: Analitik KPI unit & KPI Pegawai"])

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

import re # Tambahkan ini untuk logika filter Unit Induk ke Simprod

# =========================================================================
# TAB 2: SUKSESI JABATAN KOSONG & PROFILER TALENT
# =========================================================================
with tab2:
    st.header("🎯 Perencanaan Pengisian Jabatan Kosong (Suksesi)")
    st.write("💡 **Tips Interaktif:** Klik pada baris tabel untuk menelusuri posisi kosong hingga memunculkan rekomendasi kandidat.")

    df_jabatan_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()
    keywords_staff = ['officer', 'technician', 'tugas belajar', 'specialist', 'analyst']
    df_jabatan_kosong = df_jabatan_kosong[~df_jabatan_kosong['Jabatan'].str.lower().str.contains('|'.join(keywords_staff), na=False)]

    # --- LEVEL 1: Sebaran Jabatan Kosong per Unit Induk ---
    st.subheader("📊 Level 1: Proyeksi Lowongan Jabatan Struktural per Unit Induk")
    summary_vacancy_ui = df_jabatan_kosong.groupby('Company Name').size().reset_index(name='Total Posisi Butuh Suksesi')
    summary_vacancy_ui = summary_vacancy_ui.sort_values(by='Total Posisi Butuh Suksesi', ascending=False)
    
    event_vac_ui = st.dataframe(summary_vacancy_ui, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

    if len(event_vac_ui.selection.rows) > 0:
        selected_vac_ui = summary_vacancy_ui.iloc[event_vac_ui.selection.rows[0]]['Company Name']
        
        # --- LEVEL 2: Detail Jabatan Kosong ---
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
            
            # --- LEVEL 3: Rekomendasi Daftar Calon (FILTER KETAT) ---
            st.divider()
            st.subheader(f"👥 Level 3: Kandidat Suksesor (Kesesuaian Dahan: {dahan_profesi_target})")
            st.caption("Menampilkan eksklusif kandidat berstatus 'Promotable' & 'Solid Contributor'.")
            
            # [PEMBARUAN] Logika filter Talent Box ditambahkan di sini
            kandidat_pool = profiler[
                (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
                (profiler['NIP'] != nip_pejabat_saat_ini) &
                (profiler['Name_Box_Talent'].isin(['Promotable', 'Solid Contributor'])) &
                (profiler['Status_Ketersediaan'] == 'Available')
            ].copy()
             
            if not kandidat_pool.empty:
                event_kandidat = st.dataframe(kandidat_pool[['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name', 'Name_Box_Talent', 'Status_Ketersediaan']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
                
                # --- LEVEL 4: Review Profil & Radar Kompetensi Ekstensif ---
                if len(event_kandidat.selection.rows) > 0:
                    data_talent = kandidat_pool.iloc[event_kandidat.selection.rows[0]]
                    
                    st.divider()
                    st.subheader(f"🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent['Nama Lengkap']}")
                    
                    col_profil, col_radar = st.columns([1, 1.5]) 
                    with col_profil:
                        st.markdown(f"**NIP:** `{data_talent['NIP']}`")
                        st.markdown(f"**Asal Unit Induk:** {data_talent['Company Name']}")
                        st.markdown(f"**Jabatan Saat Ini:** {data_talent['Jabatan']}")
                        
                        bt = data_talent['Name_Box_Talent'] if pd.notna(data_talent['Name_Box_Talent']) else "Data Belum Tersedia"
                        st.info(f"📊 **9-Box Talent Placement:** {bt}")
                        
                        if "Not Available" in data_talent['Status_Ketersediaan']:
                            st.error(f"⚠️ **Status Suksesi:** {data_talent['Status_Ketersediaan']}")
                        else:
                            st.success(f"✅ **Status Suksesi:** {data_talent['Status_Ketersediaan']}")
                    
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
            else:
                st.warning("Tidak ditemukan kandidat dengan Box Talent 'Promotable' atau 'Solid Contributor' yang satu dahan profesi dan berstatus Available.")

# =========================================================================
# TAB 3: ANALITIK KPI UNIT INDUK VS KPI INDIVIDU
# =========================================================================
with tab3:
    st.header("📈 Analitik Korelasi: KPI Unit vs KPI Individu")
    st.write("Modul ini membandingkan distribusi nilai kinerja pegawai secara individu terhadap tren pencapaian operasional unit kerjanya.")
    
    df_kinerja_latest = kinerja.sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    df_kinerja_peg = df_kinerja_latest.merge(pegawai[['NIP', 'Nama Lengkap', 'Company Name', 'Business Area', 'Jabatan']], on='NIP', how='inner')
    
    list_ui_kpi = ["-- Pilih Unit Induk --"] + list(df_kinerja_peg['Company Name'].dropna().unique())
    selected_ui_kpi = st.selectbox("👉 Pilih Unit Induk untuk Analisis KPI:", list_ui_kpi)
    
    if selected_ui_kpi != "-- Pilih Unit Induk --":
        df_kpi_ui = df_kinerja_peg[df_kinerja_peg['Company Name'] == selected_ui_kpi].copy()
        avg_kpi_individu = df_kpi_ui['Nilai_Kinerja_Semester'].mean()
        
        st.divider()
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("Distribusi KPI Individu (Pegawai)")
            st.metric(f"Rata-rata Nilai Kinerja Individu", f"{avg_kpi_individu:.2f}")
            
            fig_dist = px.histogram(
                df_kpi_ui, x='Nilai_Kinerja_Semester', nbins=20, 
                title=f"Sebaran Nilai Kinerja di {selected_ui_kpi}",
                color_discrete_sequence=['#00A2E9'], labels={'Nilai_Kinerja_Semester': 'Nilai', 'count': 'Jumlah Pegawai'}
            )
            fig_dist.update_layout(bargap=0.1)
            st.plotly_chart(fig_dist, use_container_width=True)
            
        with colB:
            st.subheader("Performa Operasional Unit (Simprod)")
            
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
                    # --- [PEMBARUAN: REGEX PENCARI KATA KUNCI LOKASI INTI] ---
                    # Memotong awalan penamaan struktural yang sering tidak konsisten antar sistem
                    core_up_name = re.sub(r'^(UP3|UP2\w|ULP|UPT|UPDK|UPK|UID|UIK|UIP\w*|UIT|UIW|AREA|SEKTOR|TRAGI|UNIT PELAKSANA[\w\s]*)\s+', '', unit_operasional, flags=re.IGNORECASE).strip()
                    
                    # Mencari kecocokan di Simprod menggunakan kata kunci inti (Contoh: mencari "Serpong" pada "AREA SERPONG")
                    df_simprod_unit = simprod[
                        simprod['unit_name'].str.contains(core_up_name, case=False, na=False)
                    ].sort_values(['periode_year', 'periode_part']).copy()
                    
                    df_simprod_unit['Periode'] = df_simprod_unit['periode_year'].astype(str) + " - S" + df_simprod_unit['periode_part'].astype(str)
                    
                    if not df_simprod_unit.empty:
                        # [TAMBAHAN] Menampilkan nama asli di Simprod agar transparan kepada user
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
                    
        st.divider()
        st.subheader(f"🏆 Top Performers (KPI Individu Tertinggi di {selected_ui_kpi})")
        top_performers = df_kpi_ui.nlargest(10, 'Nilai_Kinerja_Semester')
        st.dataframe(top_performers[['NIP', 'Nama Lengkap', 'Jabatan', 'Business Area', 'Nilai_Kinerja_Semester']], use_container_width=True, hide_index=True)
