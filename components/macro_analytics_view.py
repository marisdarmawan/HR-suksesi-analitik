import streamlit as st
import plotly.express as px
import pandas as pd
from utils.preprocessor import calculate_macro_succession, calculate_career_velocity 
from utils.preprocessor import calculate_macro_succession, calculate_career_velocity, calculate_time_to_fill

def render_macro_analytics_tab(db, selected_unit="-- Semua Unit --"):
    st.header("🚁 Analitik Makro: Kesehatan Suksesi & Kecepatan Karir")
    st.write("Modul ini memberikan *Helicopter View* terhadap strategi Talent Management secara keseluruhan.")
    
    # ==========================================================
    # 0. FILTER DATA & KALKULASI DINAMIS
    # ==========================================================
    df_pegawai = db['pegawai'].copy()
    df_profiler = db['profiler'].copy()
    df_riwayat = db.get('riwayat', pd.DataFrame()).copy()
    
    # Terapkan filter jika unit dipilih
    if selected_unit != "-- Semua Unit --":
        df_pegawai = df_pegawai[df_pegawai['Company Name'].str.upper() == selected_unit.upper()]
        
        # Filter riwayat jabatan khusus untuk pegawai yang SAAT INI ada di unit tersebut
        if not df_riwayat.empty:
            nip_col_riwayat = 'NIP' if 'NIP' in df_riwayat.columns else 'nip'
            nips_di_unit = df_pegawai['NIP'].unique()
            df_riwayat = df_riwayat[df_riwayat[nip_col_riwayat].isin(nips_di_unit)]
    
    # Smart Caching: Gunakan cache untuk global, hitung ulang (on-the-fly) untuk unit spesifik
    if selected_unit == "-- Semua Unit --" and 'macro_metrics' in db:
        macro = db['macro_metrics']
    else:
        macro = calculate_macro_succession(df_pegawai, df_profiler)
        
    # Smart Caching untuk Career Velocity
    if selected_unit == "-- Semua Unit --" and 'career_velocity' in db:
        velo = db['career_velocity']
    else:
        velo = calculate_career_velocity(df_riwayat)
    
    # ==========================================================
    # 1. SUCCESSION COVERAGE & BOTTLENECK
    # ==========================================================
    st.subheader(f"1. Pemetaan Ketersediaan Suksesor ({selected_unit})")
    
    col1, col2 = st.columns([1, 1.2]) 
    
    with col1:
        st.info("💡 **Talent Dependency (Risiko Bottleneck)**")
        st.metric("Kandidat Tumpang Tindih (>3 Jabatan Target)", f"{macro.get('kandidat_overload', 0)} Orang")
        st.metric("Persentase Overload Kandidat", f"{macro.get('pct_overload', 0):.1f}%")
        st.caption("Semakin tinggi persentasenya, semakin unit ini bergantung pada segelintir 'Bintang' yang sama untuk banyak posisi.")

        df_kandidat_ovl = macro.get('df_kandidat_overload', pd.DataFrame())
        with st.expander("🔍 Klik untuk melihat Daftar Kandidat Tumpang Tindih", expanded=False):
            if not df_kandidat_ovl.empty:
                st.write("👉 *Klik baris nama untuk melihat detail target jabatan:*")
                event_kandidat = st.dataframe(
                    df_kandidat_ovl, 
                    use_container_width=True, hide_index=True, 
                    on_select="rerun", selection_mode="single-row"
                )
                
                if len(event_kandidat.selection.rows) > 0:
                    idx_terpilih = event_kandidat.selection.rows[0]
                    nip_terpilih = df_kandidat_ovl.iloc[idx_terpilih]['NIP']
                    nama_terpilih = df_kandidat_ovl.iloc[idx_terpilih]['Nama Lengkap']
                    
                    st.divider()
                    st.markdown(f"🎯 **Target untuk: {nama_terpilih}**")
                    df_mapping = macro.get('df_mapping', pd.DataFrame())
                    target_jabatan = df_mapping[df_mapping['NIP'] == nip_terpilih]
                    
                    st.dataframe(
                        target_jabatan[['Target Jabatan', 'Target Unit', 'Alasan Kosong (EWS)']], 
                        use_container_width=True, hide_index=True
                    )
            else:
                st.success("Tidak ada kandidat yang menanggung beban tumpang tindih berlebih di unit ini.")

    with col2:
        df_pie = pd.DataFrame({
            'Status': ['Memiliki Suksesor', 'Tidak Ada Suksesor'],
            'Nilai': [macro.get('pct_ada_suksesor', 0), macro.get('pct_tanpa_suksesor', 0)]
        })
        
        fig_pie = px.pie(
            df_pie, values='Nilai', names='Status', hole=0.4, 
            title="Status Pemenuhan Formasi Kosong/EWS",
            color='Status', color_discrete_map={'Memiliki Suksesor': '#22C55E', 'Tidak Ada Suksesor': '#EF4444'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        df_tanpa = macro.get('df_tanpa_suksesor', pd.DataFrame())
        with st.expander("🚨 Klik untuk melihat Daftar Jabatan Tidak Memiliki Suksesor", expanded=False):
            if not df_tanpa.empty:
                st.write("Posisi struktural di bawah ini mengalami krisis kandidat suksesor yang memenuhi syarat kualifikasi.")
                st.dataframe(
                    df_tanpa[['Jabatan', 'Company Name', 'Business Area', 'Status_EWS']], 
                    use_container_width=True, hide_index=True
                )
            else:
                st.success("✅ Seluruh formasi EWS/Kosong di unit ini memiliki kandidat suksesor yang valid.")

    st.divider()

    # ==========================================================
    # 2. KECEPATAN KARIR (BOX PLOT INTERAKTIF)
    # ==========================================================
    st.subheader(f"2. Distribusi Kecepatan Karir ({selected_unit})")
    st.write("Box plot di bawah menunjukkan sebaran waktu yang dibutuhkan pegawai untuk promosi. **Pilih/Klik pada titik outlier** (titik-titik di luar kotak) untuk melihat detail karir pegawai tersebut.")
    
    # Pastikan data berupa DataFrame (Format baru)
    df_velo = velo.copy() if isinstance(velo, pd.DataFrame) else pd.DataFrame()
    
    if not df_velo.empty:
        # Tarik data Nama Lengkap dari profiler agar bisa ditampilkan saat diklik
        df_nama = db['profiler'][['NIP', 'Nama Lengkap']].drop_duplicates()
        df_velo = df_velo.merge(df_nama, on='NIP', how='left')
        df_velo['Nama Lengkap'] = df_velo['Nama Lengkap'].fillna('Nama Tidak Ditemukan')

        # Urutan transisi agar rapi dari bawah ke atas
        urutan_fase = ['Man. Atas ➔ Man. Atas Khusus', 'Man. Menengah ➔ Man. Atas', 'Man. Dasar ➔ Man. Menengah', 'Generalist ➔ Man. Dasar']

        # Gambar Box Plot
        fig_box = px.box(
            df_velo, 
            x='Waktu (Tahun)', 
            y='Fase Transisi', 
            color='Fase Transisi',
            points='outliers', # Menampilkan outlier sebagai titik terpisah
            hover_data=['Nama Lengkap', 'NIP'], # Menyimpan data untuk deteksi klik
            orientation='h',
            category_orders={'Fase Transisi': urutan_fase},
            color_discrete_sequence=['#0C2340', '#00A2E9', '#00A2E9', '#00A2E9']
        )
        fig_box.update_layout(xaxis_title="Waktu Promosi (Tahun)", yaxis_title="", showlegend=False)
        
        # Eksekusi Render interaktif
        event_box = st.plotly_chart(fig_box, use_container_width=True, on_select="rerun", selection_mode="points")
        
        # ------------------------------------------------------
        # Logika Jika Titik Outlier Diklik
        # ------------------------------------------------------
        if len(event_box.selection.points) > 0:
            pt = event_box.selection.points[0]
            
            # Plotly menyimpan 'hover_data' di dalam array 'customdata'
            if 'customdata' in pt:
                nama_klik = pt['customdata'][0] 
                nip_klik = pt['customdata'][1]
                fase_klik = pt['y']
                
                # Filter detail transisi dari data mentah
                detail = df_velo[(df_velo['NIP'] == nip_klik) & (df_velo['Fase Transisi'] == fase_klik)]
                
                if not detail.empty:
                    st.divider()
                    st.markdown(f"🕵️‍♂️ **Detail Histori Karir: {nama_klik}** ({nip_klik})")
                    st.dataframe(
                        detail[['Fase Transisi', 'Jabatan Sebelum', 'Jabatan Setelah', 'Waktu (Tahun)']], 
                        use_container_width=True, hide_index=True
                    )
    else:
        st.info(f"Belum ada data historis transisi karir yang memadai untuk populasi pegawai di {selected_unit}.")

    st.divider()

    # ==========================================================
    # 3. ANALITIK DURASI PENGISIAN JABATAN (TIME-TO-FILL)
    # ==========================================================
    st.subheader(f"3. Durasi Pengisian Suksesor Jabatan ({selected_unit})")
    st.write("Analitik waktu historis yang dibutuhkan untuk mengisi kursi kosong, dari yang paling responsif hingga yang memakan waktu paling lama.")
    
    # Mengambil data riil menggunakan fungsi kalkulasi dari preprocessor
    df_durasi = calculate_time_to_fill(df_riwayat)

    # Pastikan data hasil kalkulasi tidak kosong dan minimal ada 2 baris agar grafik tidak error
    if not df_durasi.empty and len(df_durasi) >= 2:
        df_tercepat = df_durasi.nsmallest(10, 'Durasi_Hari').sort_values('Durasi_Hari', ascending=True)
        df_terlama = df_durasi.nlargest(10, 'Durasi_Hari').sort_values('Durasi_Hari', ascending=True)

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🚀 10 Posisi dengan Pengisian Tercepat**")
            fig_cepat = px.bar(
                df_tercepat, x='Durasi_Hari', y='Jabatan', text='Durasi_Hari',
                orientation='h',
                color='Durasi_Hari', color_continuous_scale=['#22C55E', '#86EFAC']
            )
            fig_cepat.update_layout(xaxis_title="", yaxis_title="Durasi (Hari)", xaxis_tickangle=-45, showlegend=False)
            fig_cepat.update_traces(texttemplate='%{text} Hr', textposition='outside')
            st.plotly_chart(fig_cepat, use_container_width=True)

        with col2:
            st.markdown("**🐌 10 Posisi dengan Pengisian Terlama**")
            fig_lama = px.bar(
                df_terlama, x='Durasi_Hari', y='Jabatan', text='Durasi_Hari',
                orientation='h',
                color='Durasi_Hari', color_continuous_scale=['#FCA5A5', '#EF4444']
            )
            fig_lama.update_layout(xaxis_title="", yaxis_title="Durasi (Hari)", xaxis_tickangle=-45, showlegend=False)
            fig_lama.update_traces(texttemplate='%{text} Hr', textposition='outside')
            st.plotly_chart(fig_lama, use_container_width=True)
    else:
        # Peringatan ini akan muncul jika data riwayat jabatan buatan (sintetik) 
        # tidak memiliki tanggal start_date & end_date yang berkesinambungan
        st.info("⚠️ Data riwayat jabatan saat ini belum memiliki histori pergerakan tanggal (start_date & end_date) yang memadai untuk menghitung durasi kekosongan kursi.")