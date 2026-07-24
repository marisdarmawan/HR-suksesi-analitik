import streamlit as st
import plotly.express as px
import pandas as pd

# Import parameter dari config
from config import KEYWORDS_STAFF_REGEX, ELIGIBLE_TALENT_BOX

# Import aturan bisnis Perdir PLN
from utils.business_logic import get_official_category, is_eligible

# (Asumsi: fungsi render UI profil akan kita pisahkan di profile_card.py)
from components.profile_card import render_profil_eksekutif, render_riwayat_jabatan

def render_succession_tab(db, selected_unit):
    """
    Me-render Tab 2: Perencanaan Pengisian Jabatan Struktural.
    Menampilkan posisi yang kosong dan merekomendasikan kandidat suksesor.
    """
    st.header("🎯 Perencanaan Pengisian Jabatan Struktural (Suksesi)")
    st.markdown('<div class="tips-box">💡 <b>Tips Interaktif:</b> Klik pada kotak treemap atau baris tabel untuk menelusuri posisi kosong hingga memunculkan rekomendasi kandidat.</div>', unsafe_allow_html=True)
    
    # ----------------------------------------------------------
    # 1. PERSIAPAN DATA (Filter Posisi Kosong & Non-Staff)
    # ----------------------------------------------------------
    pegawai = db['pegawai']
    profiler = db['profiler']
    
    if selected_unit != "-- Semua Unit --":
        st.caption(f"🏢 Menampilkan data khusus untuk unit: **{selected_unit}**")
        df_jabatan_kosong = pegawai[(pegawai['Company Name'].str.upper() == selected_unit.upper()) & (pegawai['Status_EWS'] != 'Aman')].copy()
    else:
        df_jabatan_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()

    # Buang posisi staff dari daftar suksesi menggunakan regex dari config
    df_jabatan_kosong = df_jabatan_kosong[~df_jabatan_kosong['Jabatan'].str.lower().str.contains(KEYWORDS_STAFF_REGEX, regex=True, na=False)]

    if df_jabatan_kosong.empty:
        st.success("✅ Tidak ada jabatan struktural yang memerlukan suksesi saat ini.")
        return

    # Metrik Utama
    mv1, mv2 = st.columns(2)
    mv1.metric("Jumlah Jabatan Struktural Perlu Suksesi", f"{len(df_jabatan_kosong):,}")
    mv2.metric("Jumlah Unit Induk Perlu Suksesi", f"{df_jabatan_kosong['Company Name'].nunique():,}")
    st.divider()

    # ----------------------------------------------------------
    # 2. LEVEL 1: TREEMAP PROYEKSI LOWONGAN
    # ----------------------------------------------------------
    st.subheader("📊 Level 1: Proyeksi Lowongan Jabatan Struktural per Unit Induk")
    summary_vacancy_ui = df_jabatan_kosong.groupby('Company Name').size().reset_index(name='Total Posisi Butuh Suksesi')
    summary_vacancy_ui = summary_vacancy_ui.sort_values(by='Total Posisi Butuh Suksesi', ascending=False)

    fig_vac_ui = px.treemap(
        summary_vacancy_ui, path=['Company Name'], values='Total Posisi Butuh Suksesi',
        color='Total Posisi Butuh Suksesi', color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
    )
    fig_vac_ui.update_traces(textinfo="label+value", texttemplate="%{label}<br>%{value} posisi")
    fig_vac_ui.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    
    event_vac_ui = st.plotly_chart(fig_vac_ui, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_vacancy_ui")

    # Jika pengguna belum memilih Unit Induk, hentikan render ke bawah (Early Return)
    if len(event_vac_ui.selection.points) == 0:
        return

    # ----------------------------------------------------------
    # 3. LEVEL 2: TABEL DETAIL POSISI TERBUKA
    # ----------------------------------------------------------
    selected_vac_ui = event_vac_ui.selection.points[0].get("label")
    st.divider()
    st.subheader(f"🔍 Level 2: Detail Posisi Jabatan Struktural Terbuka di {selected_vac_ui}")
    
    df_filtered_vac = df_jabatan_kosong[df_jabatan_kosong['Company Name'] == selected_vac_ui]
    summary_vac_detail = df_filtered_vac.groupby(['Business Area', 'Personal Sub Area', 'Jabatan', 'Status_EWS', 'Kode dan Dahan Profesi', 'NIP']).size().reset_index(name='Kasus')
    summary_vac_detail.rename(columns={'Status_EWS': 'Alasan Kebutuhan Suksesi'}, inplace=True)
    
    event_vac_up = st.dataframe(
        summary_vac_detail[['Business Area', 'Personal Sub Area', 'Jabatan', 'Alasan Kebutuhan Suksesi']], 
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
    )

    # Early return jika belum ada posisi yang diklik
    if len(event_vac_up.selection.rows) == 0:
        return

    # ----------------------------------------------------------
    # 4. LEVEL 3: REKOMENDASI KANDIDAT (ALGORITMA SUKSESI)
    # ----------------------------------------------------------
    idx_vac_up = event_vac_up.selection.rows[0]
    row_target = summary_vac_detail.iloc[idx_vac_up]
    
    dahan_profesi_target = row_target['Kode dan Dahan Profesi']
    nip_pejabat_saat_ini = row_target['NIP']
    target_career_level = get_official_category(row_target['Jabatan'], 0, row_target['Business Area'])

    st.divider()
    st.subheader(f"👥 Level 3: Kandidat Suksesor (Kesesuaian Dahan: {dahan_profesi_target})")
    st.caption(f"Target Posisi diidentifikasi sebagai **{target_career_level}**. Algoritma menyaring kandidat berdasarkan kepatuhan mutlak pada **Perdir No. 0050/2023**.")
    
    # Filter 1: Syarat Mutlak (Dahan sama, Bukan pejabat saat ini, Box Talent unggul, dan Available)
    kandidat_pool = profiler[
        (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
        (profiler['NIP'] != nip_pejabat_saat_ini) &
        (profiler['Name_Box_Talent'].isin(ELIGIBLE_TALENT_BOX)) &
        (profiler['Status_Ketersediaan'] == 'Available')
    ].copy()
    
    if kandidat_pool.empty:
        st.warning("Tidak ditemukan kandidat dengan Box Talent 'Promotable/Solid' yang satu dahan profesi dan berstatus Available.")
        return
        
    # Filter 2: Kelayakan Kepangkatan (Perdir) - Menggunakan fungsi dari business_logic.py
    kandidat_pool = kandidat_pool[kandidat_pool.apply(
        lambda x: is_eligible(x['Career_Level'], x['Person Grade'], target_career_level), axis=1
    )]
    
    if kandidat_pool.empty:
        st.error("⚠️ Kandidat yang tersedia tidak memenuhi syarat pola Jenjang Karir / Person Grade yang ditetapkan pada dokumen Peraturan Pelaksana.")
        return

    # Kalkulasi Skor Akhir
    kandidat_pool['Nilai_Kinerja_Semester'] = kandidat_pool['Nilai_Kinerja_Semester'].fillna(0)
    kandidat_pool['Nilai_Assessment_UPAC'] = kandidat_pool['Nilai_Assessment_UPAC'].fillna(0)
    kandidat_pool['Skor_Suksesi_Final'] = kandidat_pool['Nilai_Kinerja_Semester'] + kandidat_pool['Nilai_Assessment_UPAC']
    kandidat_pool = kandidat_pool.sort_values(by='Skor_Suksesi_Final', ascending=False)
    
    # Render Podium Top 3
    st.markdown("#### 🏅 Top 3 Kandidat Rekomendasi")
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
                # Gunakan session state untuk melacak klik dari tombol podium
                if st.button(f"👤 {cand['Nama Lengkap']}", key=f"podium_{i}_{cand['NIP']}", use_container_width=True):
                    st.session_state['selected_kandidat_nip'] = cand['NIP']
            else:
                st.caption("Belum ada kandidat lain.")

    st.divider()
    kolom_tampil = ['NIP', 'Nama Lengkap', 'Jabatan', 'Career_Level', 'Name_Box_Talent', 'Skor_Suksesi_Final']
    event_kandidat = st.dataframe(kandidat_pool[kolom_tampil], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

    # ----------------------------------------------------------
    # 5. LEVEL 4: DETAIL PROFIL KANDIDAT
    # ----------------------------------------------------------
    selected_nip_talent = None
    
    # Cek apakah pengguna memilih dari tabel atau dari tombol podium
    if len(event_kandidat.selection.rows) > 0:
        selected_nip_talent = kandidat_pool.iloc[event_kandidat.selection.rows[0]]['NIP']
        st.session_state['selected_kandidat_nip'] = selected_nip_talent # Sinkronisasi state
    elif st.session_state.get('selected_kandidat_nip') in kandidat_pool['NIP'].values:
        selected_nip_talent = st.session_state['selected_kandidat_nip']

    if selected_nip_talent is not None:
        data_talent = kandidat_pool[kandidat_pool['NIP'] == selected_nip_talent].iloc[0]
        
        st.divider()
        st.subheader(f"🎯 Level 4: Profil Kompetensi Eksekutif - {data_talent['Nama Lengkap']}")
        
        # Panggil fungsi UI dari profile_card.py (agar tampilan seragam dengan search global)
        render_profil_eksekutif(data_talent, target_career_level)
        render_riwayat_jabatan(db['riwayat'], data_talent['NIP'])