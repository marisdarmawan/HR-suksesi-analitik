import streamlit as st
import plotly.express as px
import pandas as pd
import re

# Import fungsi transformasi data
from utils.preprocessor import prep_kpi_distribution

def render_kpi_tab(db, selected_unit_filter):
    """
    Me-render Tab 3: Analitik Korelasi KPI Unit vs KPI Individu.
    Mencakup distribusi metrik individu dan integrasi performa operasional (Simprod).
    """
    st.header("📈 Analitik Korelasi: KPI Unit vs KPI Individu")
    st.write("Modul ini membandingkan distribusi nilai kinerja pegawai secara individu terhadap tren pencapaian operasional unit kerjanya.")
    
    # ----------------------------------------------------------
    # 1. PERSIAPAN DATA KINERJA
    # ----------------------------------------------------------
    # Ambil nilai kinerja semester terbaru untuk tiap NIP
    df_kinerja_latest = db['kinerja'].sort_values('Periode_Penilaian_Kinerja').drop_duplicates('NIP', keep='last')
    df_kinerja_peg = df_kinerja_latest.merge(
        db['pegawai'][['NIP', 'Nama Lengkap', 'Company Name', 'Business Area', 'Jabatan']], 
        on='NIP', how='inner'
    )
    
    list_ui_kpi = ["-- Pilih Unit Induk --"] + sorted(df_kinerja_peg['Company Name'].dropna().unique())

    # Sinkronisasi otomatis dengan filter di Sidebar
    default_index_kpi = 0
    if selected_unit_filter != "-- Semua Unit --":
        match_unit_kpi = [u for u in list_ui_kpi if str(u).upper() == selected_unit_filter.upper()]
        if match_unit_kpi:
            default_index_kpi = list_ui_kpi.index(match_unit_kpi[0])
            st.caption(f"🔒 Filter global aktif — otomatis menampilkan analisis KPI untuk **{selected_unit_filter}**.")
        else:
            st.warning(f"Unit **{selected_unit_filter}** dari filter global belum memiliki data KPI di modul ini.")

    selected_ui_kpi = st.selectbox("👉 Pilih Unit Induk untuk Analisis KPI:", list_ui_kpi, index=default_index_kpi)
    
    # ----------------------------------------------------------
    # 2. RENDER DISTRIBUSI KPI INDIVIDU
    # ----------------------------------------------------------
    if selected_ui_kpi != "-- Pilih Unit Induk --":
        df_kpi_ui_raw = df_kinerja_peg[df_kinerja_peg['Company Name'] == selected_ui_kpi].copy()
        
        # Lempar ke preprocessor untuk menghitung binning 15 rentang & kategori warna
        df_kpi_ui, df_bar, avg_kpi_individu = prep_kpi_distribution(df_kpi_ui_raw)
        
        st.divider()
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("Distribusi KPI Individu (Pegawai)")
            st.metric(f"Rata-rata Nilai Kinerja Individu", f"{avg_kpi_individu:.2f}")
            
            fig_dist = px.bar(
                df_bar, x='Label Rentang', y='Jumlah Pegawai', 
                title=f"Sebaran Nilai Kinerja di {selected_ui_kpi}",
                color='Kategori',
                color_discrete_map={'Di Atas Rata-rata (Hijau)': '#22C55E', 'Di Bawah Rata-rata (Merah)': '#EF4444'}
            )
            fig_dist.update_xaxes(categoryorder='array', categoryarray=df_bar['Label Rentang'].tolist())
            fig_dist.update_layout(legend_title_text='', margin=dict(t=40, b=0))

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
        st.subheader(f"🏆 Top 10 Performers (Kinerja Individu Tertinggi)")
        top_performers = df_kpi_ui.nlargest(10, 'Nilai_Kinerja_Semester')
        st.dataframe(top_performers[['NIP', 'Nama Lengkap', 'Jabatan', 'Business Area', 'Nilai_Kinerja_Semester']], use_container_width=True, hide_index=True)

        # ----------------------------------------------------------
        # 3. RENDER PERFORMA OPERASIONAL UNIT (SIMPROD)
        # ----------------------------------------------------------
        st.divider()
        st.subheader("⚙️ Performa Operasional Unit (Simprod)")
        
        simprod = db['simprod']
        hcbp = db['hcbp']
        
        if simprod.empty:
            st.info("Data Simprod belum terintegrasi untuk disandingkan.")
            return

        ui_terpilih_upper = selected_ui_kpi.upper()
        df_hcbp_filtered = hcbp[hcbp['UNIT INDUK'].str.upper() == ui_terpilih_upper]
        
        if not df_hcbp_filtered.empty:
            list_unit_ops = sorted(df_hcbp_filtered['UNIT PELAKSANA'].dropna().unique())
        else:
            st.warning("Nama Unit Induk ini belum terpetakan di dokumen Master HCBP.")
            list_unit_ops = ["-- Cari Manual --"] + sorted(simprod['unit_name'].dropna().unique())
        
        unit_operasional = st.selectbox(f"Pilih Unit Pelaksana di {selected_ui_kpi}:", list_unit_ops)
        
        if unit_operasional and unit_operasional != "-- Cari Manual --":
            # Regex untuk membuang prefix unit (UP3, ULP, UIT, dll) agar bisa dicocokkan dengan nama di Simprod
            core_up_name = re.sub(r'^(UP3|UP2\w|ULP|UPT|UPDK|UPK|UID|UIK|UIP\w*|UIT|UIW|AREA|SEKTOR|TRAGI|UNIT PELAKSANA[\w\s]*)\s+', '', unit_operasional, flags=re.IGNORECASE).strip()
            
            df_simprod_unit = simprod[simprod['unit_name'].str.contains(core_up_name, case=False, na=False)].copy()
            df_simprod_unit = df_simprod_unit.sort_values(['periode_year', 'periode_part'])
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