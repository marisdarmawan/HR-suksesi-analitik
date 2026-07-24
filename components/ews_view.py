import streamlit as st
import plotly.express as px
import pandas as pd

def render_ews_tab(db, selected_unit):
    """
    Me-render Tab 1: Peta Kerawanan Suksesi Jabatan (EWS).
    Menampilkan metrik dan chart drill-down (Level 1 ke Level 3).
    """
    st.header("🚨 Peta Kerawanan Suksesi Jabatan (EWS)")
    st.markdown('<div class="tips-box">💡 <b>Tips Interaktif:</b> Klik pada salah satu kotak di treemap atau baris tabel untuk menelusuri data secara mendalam (<i>Deep Dive</i>).</div>', unsafe_allow_html=True)
    
    # ----------------------------------------------------------
    # 1. FILTERING DATA BERDASARKAN SIDEBAR
    # ----------------------------------------------------------
    pegawai = db['pegawai']
    
    if selected_unit != "-- Semua Unit --":
        st.caption(f"🏢 Menampilkan data khusus untuk unit: **{selected_unit}**")
        df_ews_aktif = pegawai[(pegawai['Company Name'].str.upper() == selected_unit.upper()) & (pegawai['Status_EWS'] != 'Aman')].copy()
    else:
        df_ews_aktif = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()

    # Jika tidak ada kasus EWS
    if df_ews_aktif.empty:
        st.success("✅ Tidak ada personil yang masuk ke dalam radar peringatan (EWS) untuk filter saat ini.")
        return

    # ----------------------------------------------------------
    # 2. RENDER TOP METRICS
    # ----------------------------------------------------------
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Kasus EWS", f"{len(df_ews_aktif):,}")
    m2.metric("Mendekati Pensiun", f"{int(df_ews_aktif['Status_EWS'].str.contains('Pensiun').sum()):,}")
    m3.metric("Over SLA Jabatan", f"{int(df_ews_aktif['Status_EWS'].str.contains('Over SLA').sum()):,}")
    st.caption("ℹ️ Satu pegawai bisa masuk ke *kedua* kategori sekaligus (Mendekati Pensiun **dan** Over SLA).")
    st.divider()

    # ----------------------------------------------------------
    # 3. LEVEL 1: TREEMAP UNIT INDUK
    # ----------------------------------------------------------
    st.subheader("📊 Level 1: Jumlah Kasus EWS per Unit Induk")
    summary_unit_induk = df_ews_aktif.groupby('Company Name').size().reset_index(name='Jumlah Pegawai Alert')
    
    fig_ui = px.treemap(
        summary_unit_induk, 
        path=['Company Name'], 
        values='Jumlah Pegawai Alert',
        color='Jumlah Pegawai Alert', 
        color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
        title="Jumlah Kasus EWS per Unit Induk"
    )
    fig_ui.update_traces(textinfo="label+value")
    fig_ui.update_layout(margin=dict(t=40, l=10, r=10, b=10))
    
    event_ui = st.plotly_chart(fig_ui, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_ews_ui")

    # ----------------------------------------------------------
    # 4. LEVEL 2: TREEMAP UNIT PELAKSANA (Jika Level 1 di-klik)
    # ----------------------------------------------------------
    if len(event_ui.selection.points) > 0:
        selected_ui = event_ui.selection.points[0].get("label")

        st.divider()
        st.subheader(f"🏢 Level 2: Detail Sebaran di {selected_ui}")
        df_filtered_ui = df_ews_aktif[df_ews_aktif['Company Name'] == selected_ui]
        summary_pelaksana = df_filtered_ui.groupby(['Business Area', 'Personal Sub Area']).size().reset_index(name='Jumlah Kasus')
        
        fig_up = px.treemap(
            summary_pelaksana, 
            path=['Business Area', 'Personal Sub Area'], 
            values='Jumlah Kasus',
            color='Jumlah Kasus', 
            color_continuous_scale=['#B9E4FA', '#00A2E9', '#0C2340'],
            title=f"Sebaran Kasus EWS di {selected_ui}"
        )
        fig_up.update_traces(textinfo="label+value")
        fig_up.update_layout(margin=dict(t=40, l=10, r=10, b=10))
        
        event_up = st.plotly_chart(fig_up, use_container_width=True, on_select="rerun", selection_mode="points", key="treemap_ews_up")

        # ----------------------------------------------------------
        # 5. LEVEL 3: TABEL DAFTAR KARYAWAN (Jika Level 2 di-klik)
        # ----------------------------------------------------------
        if len(event_up.selection.points) > 0:
            pt_up = event_up.selection.points[0]
            clicked_label = pt_up.get("label")
            clicked_parent = pt_up.get("parent")

            if clicked_parent:
                # Kotak anak (leaf) diklik -> Business Area = parent, Personal Sub Area = label[cite: 1]
                df_level3 = df_filtered_ui[
                    (df_filtered_ui['Business Area'] == clicked_parent) &
                    (df_filtered_ui['Personal Sub Area'] == clicked_label)
                ].copy()
                judul_level3 = clicked_label
            else:
                # Kotak induk (Business Area) diklik langsung -> tampilkan semua di bawahnya[cite: 1]
                df_level3 = df_filtered_ui[df_filtered_ui['Business Area'] == clicked_label].copy()
                judul_level3 = clicked_label

            st.divider()
            st.subheader(f"📋 Level 3: Daftar Personil Masuk Radar EWS di {judul_level3}")
            
            df_final_karyawan = df_level3
            df_final_karyawan['Lama_Menjabat_Tahun'] = df_final_karyawan['Lama_Menjabat_Tahun'].round(1)
            kolom_final = ['NIP', 'Nama Lengkap', 'Jabatan', 'Lama_Menjabat_Tahun', 'Umur Tahun', 'Status_EWS']
            
            st.dataframe(df_final_karyawan[kolom_final], use_container_width=True, hide_index=True)