import pandas as pd
import numpy as np
from config import KEYWORDS_STAFF_REGEX

# ==========================================================
# 1. PRE-PROCESSING UNTUK RIWAYAT JABATAN
# ==========================================================
def prep_riwayat_jabatan(df_riwayat, nip_kandidat):
    """
    Membersihkan, memformat tanggal, dan menghitung masa jabatan 
    untuk ditampilkan di tabel riwayat karir kandidat.
    """
    nip_col = 'NIP' if 'NIP' in df_riwayat.columns else 'nip'
    df_riwayat_kandidat = df_riwayat[df_riwayat[nip_col] == nip_kandidat].copy()
    
    # Jika data kosong, kembalikan DataFrame kosong
    if df_riwayat_kandidat.empty:
        return pd.DataFrame()
        
    # Standardisasi format datetime
    if 'start_date' in df_riwayat_kandidat.columns:
        df_riwayat_kandidat['start_date_dt'] = pd.to_datetime(df_riwayat_kandidat['start_date'], errors='coerce')
    if 'end_date' in df_riwayat_kandidat.columns:
        df_riwayat_kandidat['end_date_dt'] = pd.to_datetime(df_riwayat_kandidat['end_date'], errors='coerce')
        
    sekarang = pd.to_datetime('today')
    
    # Hitung durasi (Tahun & Bulan)
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
    
    # Potong teks organisasi agar tidak terlalu panjang (Max Level 3)
    def potong_org(org_val):
        if pd.isna(org_val): return "-"
        parts = [p.strip() for p in str(org_val).split('-')]
        return " - ".join(parts[:3])
        
    if 'organisasi' in df_riwayat_kandidat.columns:
        df_riwayat_kandidat['Organisasi (Max Level 3)'] = df_riwayat_kandidat['organisasi'].apply(potong_org)
        
    # Format string tanggal untuk UI
    df_riwayat_kandidat['Mulai Menjabat'] = df_riwayat_kandidat['start_date_dt'].dt.strftime('%d %b %Y').fillna('-') if 'start_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('start_date', '-')
    df_riwayat_kandidat['Akhir Menjabat'] = df_riwayat_kandidat['end_date_dt'].dt.strftime('%d %b %Y').fillna('Sekarang') if 'end_date_dt' in df_riwayat_kandidat.columns else df_riwayat_kandidat.get('end_date', '-')
    
    # Urutkan dari riwayat terbaru
    if 'end_date_dt' in df_riwayat_kandidat.columns:
        df_riwayat_kandidat = df_riwayat_kandidat.sort_values(by='end_date_dt', ascending=False, na_position='first')
        
    # Seleksi kolom final untuk ditampilkan
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
    
    return df_tampil


# ==========================================================
# 2. PRE-PROCESSING UNTUK DISTRIBUSI KPI (TAB 3)
# ==========================================================
def prep_kpi_distribution(df_kpi_ui):
    """
    Menyiapkan data untuk chart distribusi (histogram) KPI di suatu unit.
    Memecah nilai menjadi 15 rentang (bins) dan menentukan kategori warna.
    """
    if df_kpi_ui.empty:
        return df_kpi_ui, pd.DataFrame(), 0.0

    avg_kpi_individu = df_kpi_ui['Nilai_Kinerja_Semester'].mean()
    df_kpi_ui = df_kpi_ui.copy()
    
    # Buat rentang bins dengan pd.cut
    df_kpi_ui['Rentang Kinerja'] = pd.cut(df_kpi_ui['Nilai_Kinerja_Semester'], bins=15)
    df_kpi_ui['Label Rentang'] = df_kpi_ui['Rentang Kinerja'].apply(lambda x: f"{int(x.left)} - {int(x.right)}" if pd.notna(x) else "Unknown").astype(str)
    
    # Agregasi data untuk bar chart
    df_bar = df_kpi_ui.groupby('Label Rentang').size().reset_index(name='Jumlah Pegawai')
    
    # Sorting key agar rentang terurut dengan benar (bukan secara alfabetis)
    df_bar['Sort_Key'] = df_bar['Label Rentang'].apply(lambda x: int(x.split(' - ')[0]) if x != "Unknown" else 0)
    df_bar = df_bar.sort_values('Sort_Key')
    
    # Penentuan label warna (Di Atas / Di Bawah Rata-rata)
    df_bar['Bin_Mid'] = df_bar['Label Rentang'].apply(lambda x: (int(x.split(' - ')[0]) + int(x.split(' - ')[1])) / 2 if x != "Unknown" else 0).astype(float)
    df_bar['Kategori'] = np.where(
        df_bar['Bin_Mid'] >= avg_kpi_individu, 
        'Di Atas Rata-rata (Hijau)', 
        'Di Bawah Rata-rata (Merah)'
    )
    
    return df_kpi_ui, df_bar, avg_kpi_individu

from utils.business_logic import get_official_category, is_eligible
from config import ELIGIBLE_TALENT_BOX, KEYWORDS_STAFF_REGEX

# ==========================================================
# 3. PRE-PROCESSING UNTUK ANALITIK MAKRO (TAB 4)
# ==========================================================
def calculate_macro_succession(pegawai, profiler):
    """Menghitung Succession Coverage dan mengekstrak tabel detail Bottleneck"""
    from config import ELIGIBLE_TALENT_BOX, KEYWORDS_STAFF_REGEX
    
    # Ambil daftar jabatan yang butuh suksesi
    df_kosong = pegawai[pegawai['Status_EWS'] != 'Aman'].copy()
    df_kosong = df_kosong[~df_kosong['Jabatan'].str.lower().str.contains(KEYWORDS_STAFF_REGEX, regex=True, na=False)]
    
    mapping_kandidat_jabatan = []
    jabatan_tanpa_suksesor = []
    
    # Loop untuk simulasi pencarian
    for _, row in df_kosong.iterrows():
        tgt_level = get_official_category(row['Jabatan'], 0, row['Company Name'])
        
        # Cari kandidat potensial di dahan yang sama
        pool = profiler[
            (profiler['Kode dan Dahan Profesi'] == row['Kode dan Dahan Profesi']) & 
            (profiler['NIP'] != row['NIP']) &
            (profiler['Name_Box_Talent'].isin(ELIGIBLE_TALENT_BOX)) &
            (profiler['Status_Ketersediaan'] == 'Available')
        ]
        
        # Filter kelayakan Perdir
        suksesor_valid = pool[pool.apply(lambda x: is_eligible(x['Career_Level'], x['Person Grade'], tgt_level), axis=1)]
        
        if not suksesor_valid.empty:
            for nip in suksesor_valid['NIP']:
                mapping_kandidat_jabatan.append({
                    'NIP': nip,
                    'Target Jabatan': row['Jabatan'],
                    'Target Unit': row['Company Name'],
                    'Alasan Kosong (EWS)': row['Status_EWS']
                })
        else:
            # Simpan baris jabatan yang tidak punya suksesor
            jabatan_tanpa_suksesor.append(row)

    # ---------------------------------------------------------
    # PEMROSESAN TABEL DETAIL
    # ---------------------------------------------------------
    df_mapping = pd.DataFrame(mapping_kandidat_jabatan)
    
    if jabatan_tanpa_suksesor:
        df_tanpa_suksesor = pd.DataFrame(jabatan_tanpa_suksesor)
    else:
        df_tanpa_suksesor = pd.DataFrame(columns=['Jabatan', 'Company Name', 'Business Area', 'Status_EWS'])
        
    total_kosong = len(df_kosong)
    total_tanpa_suksesor = len(df_tanpa_suksesor)
    total_ada = total_kosong - total_tanpa_suksesor

    # Ekstraksi Detail Kandidat Tumpang Tindih (>3 Jabatan)
    df_overload = pd.DataFrame()
    kandidat_unik = 0
    overload_count = 0
    
    if not df_mapping.empty:
        kandidat_count = df_mapping['NIP'].value_counts()
        kandidat_unik = len(kandidat_count)
        
        # Filter NIP yang muncul lebih dari 3 kali
        overload_nips = kandidat_count[kandidat_count > 3].index
        overload_count = len(overload_nips)
        
        if overload_count > 0:
            df_overload = profiler[profiler['NIP'].isin(overload_nips)][['NIP', 'Nama Lengkap', 'Jabatan', 'Company Name']].copy()
            df_overload['Jumlah Target Posisi'] = df_overload['NIP'].map(kandidat_count)
            df_overload = df_overload.sort_values('Jumlah Target Posisi', ascending=False)

    return {
        'total_kosong': total_kosong,
        'pct_ada_suksesor': (total_ada / total_kosong * 100) if total_kosong > 0 else 0,
        'pct_tanpa_suksesor': (total_tanpa_suksesor / total_kosong * 100) if total_kosong > 0 else 0,
        'kandidat_unik': kandidat_unik,
        'kandidat_overload': overload_count,
        'pct_overload': (overload_count / kandidat_unik * 100) if kandidat_unik > 0 else 0,
        
        # Tambahan output tabel detail untuk UI:
        'df_tanpa_suksesor': df_tanpa_suksesor,
        'df_kandidat_overload': df_overload,
        'df_mapping': df_mapping
    }

def calculate_career_velocity(riwayat):
    """Menghitung detail riwayat transisi karir per individu (Format DataFrame untuk Box Plot)"""
    import pandas as pd
    if riwayat.empty: return pd.DataFrame()
    
    # Deteksi dinamis kolom NIP
    nip_col = 'NIP' if 'NIP' in riwayat.columns else 'nip'
    
    # Format tanggal
    riwayat['start_date'] = pd.to_datetime(riwayat['start_date'], errors='coerce')
    riwayat = riwayat.dropna(subset=['start_date']).sort_values([nip_col, 'start_date'])
    
    # Tentukan level jabatan masa lalu
    riwayat['Level'] = riwayat.apply(lambda x: get_official_category(x.get('jabatan',''), 0, x.get('organisasi','')), axis=1)
    
    # Cari baris PERTAMA KALI seseorang menyentuh suatu level
    first_touch_idx = riwayat.groupby([nip_col, 'Level'])['start_date'].idxmin()
    first_touch_rows = riwayat.loc[first_touch_idx].copy()
    
    # Ekstrak data 'Generalist' (dari berbagai level) sebagai satu titik awal (Start_Generalist)
    gen_rows = first_touch_rows[first_touch_rows['Level'].str.contains('Generalist', na=False)]
    if not gen_rows.empty:
        gen_idx = gen_rows.groupby(nip_col)['start_date'].idxmin()
        gen_first = gen_rows.loc[gen_idx].copy()
        gen_first['Level'] = 'Start_Generalist'
        first_touch_rows = pd.concat([first_touch_rows, gen_first], ignore_index=True)
        
    # Buat tabel pivot untuk mencocokkan Tanggal dan Jabatan secara horizontal per NIP
    dates_df = first_touch_rows.pivot(index=nip_col, columns='Level', values='start_date')
    jobs_df = first_touch_rows.pivot(index=nip_col, columns='Level', values='jabatan')
    
    transitions_list = []
    
    # Definisi rute transisi
    phases = [
        ('Start_Generalist', 'Manajemen Dasar', 'Generalist ➔ Man. Dasar'),
        ('Manajemen Dasar', 'Manajemen Menengah', 'Man. Dasar ➔ Man. Menengah'),
        ('Manajemen Menengah', 'Manajemen Atas', 'Man. Menengah ➔ Man. Atas'),
        ('Manajemen Atas', 'Manajemen Atas Khusus', 'Man. Atas ➔ Man. Atas Khusus')
    ]
    
    # Kalkulasi Delta (Durasi) dan tarik Jabatan Aslinya
    for col_from, col_to, label in phases:
        if col_from in dates_df.columns and col_to in dates_df.columns:
            # Filter hanya NIP yang memiliki tanggal start valid di kedua fase (promosi maju)
            valid_mask = (dates_df[col_to] > dates_df[col_from]) & dates_df[col_from].notna() & dates_df[col_to].notna()
            valid_nips = dates_df[valid_mask].index
            
            for nip in valid_nips:
                d_from = dates_df.at[nip, col_from]
                d_to = dates_df.at[nip, col_to]
                duration = (d_to - d_from).days / 365.25
                
                transitions_list.append({
                    'NIP': nip,
                    'Fase Transisi': label,
                    'Waktu (Tahun)': round(duration, 1),
                    'Jabatan Sebelum': jobs_df.at[nip, col_from],
                    'Jabatan Setelah': jobs_df.at[nip, col_to]
                })
                
    return pd.DataFrame(transitions_list)

def calculate_time_to_fill(riwayat):
    """Menghitung rata-rata durasi kekosongan jabatan (Time-to-Fill) dari data historis"""
    if riwayat.empty: return pd.DataFrame()
    
    df = riwayat.copy()
    
    # 2. Pastikan format tanggal benar dan buang data yang kosong
    df['start_date'] = pd.to_datetime(df.get('start_date'), errors='coerce')
    df['end_date'] = pd.to_datetime(df.get('end_date'), errors='coerce')
    df = df.dropna(subset=['start_date', 'jabatan'])
    
    # 3. FILTER JABATAN STRUKTURAL
    # Membuang baris riwayat yang mengandung kata kunci staf/fungsional
    df = df[~df['jabatan'].str.lower().str.contains(KEYWORDS_STAFF_REGEX, regex=True, na=False)]
    
    # 4. Urutkan berdasarkan jabatan dan tanggal mulai
    df = df.sort_values(['jabatan', 'start_date'])
    
    # 5. Cari tanggal masuk (start_date) pejabat berikutnya di kursi yang sama
    df['next_start'] = df.groupby('jabatan')['start_date'].shift(-1)
    
    # 6. Hitung selisih hari antara pejabat lama keluar dengan pejabat baru masuk
    df['gap_days'] = (df['next_start'] - df['end_date']).dt.days
    
    # 7. Filter anomali (Ambil gap yang wajar: > 0 hari dan < 730 hari/2 tahun)
    valid_gaps = df[(df['gap_days'] > 0) & (df['gap_days'] <= 730)]
    
    if valid_gaps.empty:
        return pd.DataFrame(columns=['Jabatan', 'Durasi_Hari'])
        
    # 8. Hitung rata-rata durasi per jabatan struktural
    avg_gaps = valid_gaps.groupby('jabatan')['gap_days'].mean().reset_index()
    avg_gaps.rename(columns={'jabatan': 'Jabatan', 'gap_days': 'Durasi_Hari'}, inplace=True)
    avg_gaps['Durasi_Hari'] = avg_gaps['Durasi_Hari'].round(0).astype(int)
    
    return avg_gaps