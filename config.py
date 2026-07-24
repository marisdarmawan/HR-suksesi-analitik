from pathlib import Path

# ==========================================================
# 1. PATH CONFIGURATION
# ==========================================================
# Mendapatkan path absolut dari direktori tempat config.py berada
BASE_DIR = Path(__file__).resolve().parent

# Mendefinisikan folder tempat data mentah disimpan
DATA_DIR = BASE_DIR / 'data' / 'raw'

# Pemetaan path untuk masing-masing file sumber
DATA_FILES = {
    'pegawai': DATA_DIR / 'Synthetic_Data_Pegawai_Patched.csv',
    'kinerja': DATA_DIR / 'Synthetic_Data_Kinerja.csv',
    'assessment': DATA_DIR / 'Synthetic_Data_Hasil_Assessment_Psikologis_Potensi.csv',
    'aps': DATA_DIR / 'Synthetic_APS_Data.csv',
    'riwayat': DATA_DIR / 'Synthetic_Riwayat_Jabatan_Patched.csv',
    'hcbp': DATA_DIR / 'Data HCBP.xlsx',
    'simprod': DATA_DIR / 'Simprod_Flattened.csv'
}

# ==========================================================
# 2. BUSINESS RULES & THRESHOLDS (Parameter Perdir/Aturan)
# ==========================================================
# Batas umur pensiun normal
USIA_PENSIUN_MAX = 56
USIA_WARNING_PENSIUN = 55

# Batas SLA Lama Menjabat (Tahun) untuk memicu EWS Over SLA
SLA_JABATAN_TAHUN = 4.0

# Daftar kata kunci regex untuk mengecualikan posisi staff dari suksesi struktural
# (Menggunakan format string regex)
KEYWORDS_STAFF_REGEX = r'\b(?:officer|technician|tugas belajar|specialist|analyst|cuti|generalist|tugas karya|operator|engineer|ahli)\b'

# Kata kunci khusus kandidat yang tidak bisa dipromosikan saat ini
KEYWORDS_UNAVAILABLE_REGEX = r'\b(?:cuti|tugas belajar)\b'

# ==========================================================
# 3. CONSTANTS & MAPPINGS
# ==========================================================
# Array 31 Dimensi Psikologis dari Assessment UPAC
DIMENSI_31 = [
    'CEE', 'BAC', 'DCM', 'DOR', 'PNO', 'BTR', 'COL', 'BPA', 'INF', 
    'ADA', 'CLE', 'COC', 'CIM', 'EXE', 'FCH', 'IOT', 'ABS', 'NUM', 
    'VER', 'I', 'F', 'A', 'C', 'E', 'S', 'COM', 'TMW', 'SEF', 
    'INI', 'DEC', 'SER'
]

# Kategori Box Talent yang dianggap layak promosi (Eligible)
ELIGIBLE_TALENT_BOX = ['Promotable', 'Solid Contributor', 'High Potential']

# ==========================================================
# 4. UI / STYLING CONSTANTS
# ==========================================================
# Palet warna identitas PLN untuk digunakan di visualisasi Plotly
PLN_COLORS = {
    'blue': '#00A2E9',
    'navy': '#0C2340',
    'light_blue': '#B9E4FA',
    'success': '#22C55E',
    'danger': '#EF4444'
}