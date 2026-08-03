import streamlit as st
import os
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from config import DB_URI, ELIGIBLE_TALENT_BOX
from data.data_loader import get_hr_data
from utils.business_logic import get_official_category, is_eligible
from utils.preprocessor import calculate_macro_succession, calculate_career_velocity, calculate_time_to_fill
from utils.rag_helper import query_peraturan
import pandas as pd

@tool
def alat_baca_peraturan(pertanyaan: str) -> str:
    """
    Gunakan tool ini HANYA JIKA pengguna bertanya tentang TEORI, SYARAT, ATURAN, atau ISI DOKUMEN PERATURAN (khususnya Perdir 0050/2023).
    Masukkan inti pertanyaan Anda, misalnya: "Apa saja kualifikasi jabatan Manajemen Atas?" atau "Sebutkan rentang Person Grade untuk Senior Specialist!".
    Tool ini akan mengembalikan teks kutipan referensi dari dokumen aslinya untuk Anda rangkum kembali ke pengguna.
    """
    return query_peraturan(pertanyaan)

@tool
def alat_analitik_makro(jenis_analitik: str, unit_induk: str = "") -> str:
    """
    Gunakan tool ini khusus untuk pertanyaan terkait Analitik Makro / Kalkulasi Prediktif:
    1. 'kesehatan_suksesi': untuk mencari persentase krisis kursi kosong, jumlah kandidat tumpang tindih (overload), atau ketersediaan suksesor.
    2. 'kecepatan_karir': untuk mencari rata-rata waktu/durasi yang dibutuhkan untuk promosi antar level jabatan.
    3. 'time_to_fill': untuk mencari jabatan struktural mana yang butuh waktu terlama atau tercepat untuk dicari penggantinya (durasi kekosongan kursi).
    
    Argumen:
    - jenis_analitik: Wajib diisi salah satu dari: "kesehatan_suksesi", "kecepatan_karir", "time_to_fill"
    - unit_induk: (Opsional) Masukkan nama unit induk jika spesifik (misal: "PT PLN (PERSERO) KANTOR PUSAT"). Jika ditanya keseluruhan, biarkan kosong "".
    """
    db = get_hr_data()
    df_pegawai = db['pegawai'].copy()
    df_profiler = db['profiler'].copy()
    df_riwayat = db.get('riwayat', pd.DataFrame()).copy()
    
    # Terapkan filter jika unit dipilih
    if unit_induk and unit_induk != "":
        df_pegawai = df_pegawai[df_pegawai['Company Name'].str.upper() == unit_induk.upper()]
        if not df_riwayat.empty:
            nip_col_riwayat = 'NIP' if 'NIP' in df_riwayat.columns else 'nip'
            nips_di_unit = df_pegawai['NIP'].unique()
            df_riwayat = df_riwayat[df_riwayat[nip_col_riwayat].isin(nips_di_unit)]
            
        if df_pegawai.empty:
            return f"Data untuk unit induk '{unit_induk}' tidak ditemukan atau kosong."
            
    if jenis_analitik == "kesehatan_suksesi":
        macro = calculate_macro_succession(df_pegawai, df_profiler)
        result = (
            f"--- Analitik Kesehatan Suksesi ---\n"
            f"Total Jabatan Kosong/EWS: {macro['total_kosong']}\n"
            f"Memiliki Suksesor Valid: {macro['pct_ada_suksesor']:.1f}%\n"
            f"Krisis (Tanpa Suksesor): {macro['pct_tanpa_suksesor']:.1f}%\n"
            f"Kandidat Unik Tersedia: {macro['kandidat_unik']} orang\n"
            f"Kandidat Overload (Tumpang Tindih >3 Target): {macro['kandidat_overload']} orang ({macro['pct_overload']:.1f}%)\n"
        )
        return result
        
    elif jenis_analitik == "kecepatan_karir":
        velo = calculate_career_velocity(df_riwayat)
        if velo.empty:
            return "Belum ada data historis transisi karir yang memadai untuk menghitung kecepatan karir di populasi ini."
            
        avg_velo = velo.groupby('Fase Transisi')['Waktu (Tahun)'].mean().reset_index()
        avg_velo['Waktu (Tahun)'] = avg_velo['Waktu (Tahun)'].round(1)
        
        result = "--- Rata-rata Kecepatan Karir (Tahun) ---\n"
        for _, row in avg_velo.iterrows():
            result += f"- {row['Fase Transisi']}: {row['Waktu (Tahun)']} tahun\n"
        return result
        
    elif jenis_analitik == "time_to_fill":
        df_durasi = calculate_time_to_fill(df_riwayat)
        if df_durasi.empty or len(df_durasi) < 2:
            return "Data riwayat jabatan belum memadai untuk menghitung rata-rata durasi kekosongan kursi (Time-to-Fill)."
            
        df_tercepat = df_durasi.nsmallest(5, 'Durasi_Hari')
        df_terlama = df_durasi.nlargest(5, 'Durasi_Hari')
        
        result = "--- Analitik Time-to-Fill (Durasi Pengisian Jabatan) ---\n"
        result += "Top 5 Tercepat:\n"
        for _, row in df_tercepat.iterrows():
            result += f"- {row['Jabatan']}: {row['Durasi_Hari']} Hari\n"
            
        result += "\nTop 5 Terlama (Paling Lambat):\n"
        for _, row in df_terlama.iterrows():
            result += f"- {row['Jabatan']}: {row['Durasi_Hari']} Hari\n"
            
        return result
    else:
        return f"jenis_analitik '{jenis_analitik}' tidak dikenali. Pilih: kesehatan_suksesi, kecepatan_karir, time_to_fill."
@tool
def alat_rekomendasi_suksesi(jabatan_target: str) -> str:
    """
    Gunakan tool ini HANYA JIKA Anda diminta memberikan REKOMENDASI SUKSESOR atau pengganti untuk sebuah jabatan tertentu.
    Masukkan nama jabatan yang dicari (contoh: "EXECUTIVE VICE PRESIDENT TRANSMISI KALIMANTAN, SULAWESI, MALUKU, PAPUA, DAN NUSA TENGGARA").
    Tool ini akan mengembalikan daftar rekomendasi yang sudah diverifikasi menggunakan aturan mutlak Perdir 0050/2023.
    """
    db = get_hr_data()
    profiler = db['profiler']
    
    # Cari data jabatan target di profiler
    target_row = profiler[profiler['Jabatan'].str.lower() == jabatan_target.lower()]
    if target_row.empty:
        # Coba partial match jika tidak persis
        target_row = profiler[profiler['Jabatan'].str.lower().str.contains(jabatan_target.lower(), na=False)]
        
    if target_row.empty:
        return f"Jabatan '{jabatan_target}' tidak ditemukan di database. Pastikan nama jabatannya benar."
        
    # Ambil baris pertama sebagai target valid
    target_row = target_row.iloc[0]
    
    dahan_profesi_target = target_row['Kode dan Dahan Profesi']
    nip_pejabat_saat_ini = target_row['NIP']
    target_career_level = get_official_category(target_row['Jabatan'], 0, target_row['Business Area'])
    
    # Filter 1: Dahan, Box Talent, Ketersediaan
    kandidat_pool = profiler[
        (profiler['Kode dan Dahan Profesi'] == dahan_profesi_target) & 
        (profiler['NIP'] != nip_pejabat_saat_ini) &
        (profiler['Name_Box_Talent'].isin(ELIGIBLE_TALENT_BOX)) &
        (profiler['Status_Ketersediaan'] == 'Available')
    ].copy()
    
    if kandidat_pool.empty:
        return f"Tidak ada kandidat untuk '{jabatan_target}' dengan dahan '{dahan_profesi_target}' yang masuk Box Talent unggulan dan Available."
        
    # Filter 2: Kelayakan Kepangkatan
    kandidat_pool = kandidat_pool[kandidat_pool.apply(
        lambda x: is_eligible(x['Career_Level'], x['Person Grade'], target_career_level), axis=1
    )]
    
    if kandidat_pool.empty:
        return f"Kandidat yang tersedia untuk '{jabatan_target}' tidak memenuhi syarat level/grade promosi sesuai Perdir PLN."
        
    # Kalkulasi Skor Akhir
    kandidat_pool['Nilai_Kinerja_Semester'] = pd.to_numeric(kandidat_pool['Nilai_Kinerja_Semester'], errors='coerce').fillna(0)
    kandidat_pool['Nilai_Assessment_UPAC'] = pd.to_numeric(kandidat_pool['Nilai_Assessment_UPAC'], errors='coerce').fillna(0)
    kandidat_pool['Skor_Suksesi_Final'] = kandidat_pool['Nilai_Kinerja_Semester'] + kandidat_pool['Nilai_Assessment_UPAC']
    kandidat_pool = kandidat_pool.sort_values(by='Skor_Suksesi_Final', ascending=False)
    
    # Ambil Top 5
    top5 = kandidat_pool.head(5)
    
    result = f"Rekomendasi Suksesor untuk {target_row['Jabatan']} (Target: {target_career_level}):\n"
    for i, (_, cand) in enumerate(top5.iterrows(), 1):
        result += f"{i}. {cand['Nama Lengkap']} (NIP: {cand['NIP']})\n"
        result += f"   - Jabatan Saat Ini: {cand['Jabatan']}\n"
        result += f"   - Skor Total: {int(cand['Skor_Suksesi_Final'])} (Kinerja: {cand['Nilai_Kinerja_Semester']}, UPAC: {cand['Nilai_Assessment_UPAC']})\n"
        result += f"   - Karier & Grade: {cand['Career_Level']} / Grade {cand['Person Grade']}\n"
        result += f"   - Dahan Profesi: {cand['Kode dan Dahan Profesi']}\n"
        result += f"   - Box Talent: {cand['Name_Box_Talent']}\n\n"
        
    return result
@st.cache_resource
def init_agent():
    """Inisialisasi SQL Agent dengan Langchain dan OpenAI Proxy."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "YOUR_MODEL")
    
    if not api_key or api_key == "YOUR_API_KEY":
        return None, "⚠️ OPENAI_API_KEY belum dikonfigurasi. Silakan isi di file .env."

    try:
        # Hubungkan ke PostgreSQL Database
        db = SQLDatabase.from_uri(DB_URI)
        
        # Inisialisasi LLM OpenAI / LiteLLM Proxy
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )
        
        # Guardrail System Prompt khusus untuk mencegah manipulasi data
        custom_prefix = """Anda adalah asisten AI khusus HR (Human Resources) untuk PT PLN.
Anda bertugas menjawab pertanyaan terkait data pegawai, kinerja, dan riwayat jabatan menggunakan database.

ATURAN SANGAT PENTING (GUARDRAIL):
1. Anda HANYA diizinkan untuk menjalankan query SELECT.
2. JANGAN PERNAH menjalankan query INSERT, UPDATE, DELETE, DROP, ALTER, GRANT, REVOKE.
3. JABATAN STRUKTURAL: Jika ditanya "Jabatan Struktural", kecualikan staff/non-struktural. Gunakan regex ini di query: `LOWER("Jabatan") !~ '\\y(officer|technician|tugas belajar|specialist|analyst|cuti|generalist|tugas karya|operator|engineer|ahli)\\y'`
4. JABATAN PERLU SUKSESI / KOSONG: Jika ditanya "jabatan yang perlu suksesi", "jabatan kosong", atau "EWS", Anda WAJIB memfilter pegawai struktural (aturan 3) yang memenuhi kondisi: `"Umur_Tahun" <= 56` DAN (`"Umur_Tahun" >= 55` ATAU `(CURRENT_DATE - "Start_Date_Jabatan") / 365.25 >= 4.0`). JANGAN menggunakan kolom "Status_EWS".
5. NAMA KOLOM POSTGRESQL: Karena skema dibuat dari Pandas, semua nama kolom bersifat *case-sensitive*. Anda WAJIB menggunakan tanda kutip ganda (") untuk setiap nama kolom. Contoh: `"Jabatan"`, `"Company_Name"`, `"Nama_Lengkap"`. JANGAN memanggil kolom tanpa tanda kutip.
6. REKOMENDASI SUKSESI: Jika diminta memberikan suksesor/pengganti suatu jabatan, JANGAN query SQL manual. Anda WAJIB memanggil tool "alat_rekomendasi_suksesi" dengan argumen nama jabatan yang dicari. Hasil tool sudah mengandung data yang valid sesuai Peraturan Direksi.
7. ANALITIK MAKRO (KALKULASI PREDIKTIF): Jika ditanya tentang kecepatan karir (Career Velocity), kesehatan suksesi (overload, persentase krisis kursi kosong), atau Time-to-Fill (durasi pengisian kursi yang terlama/tercepat), JANGAN query manual! Panggil tool "alat_analitik_makro" dengan "jenis_analitik" yang sesuai ("kesehatan_suksesi", "kecepatan_karir", "time_to_fill") dan opsional "unit_induk" jika ditanya untuk unit spesifik.
8. BACA DOKUMEN ATURAN (RAG): Jika ditanya tentang teori, syarat jabatan, kualifikasi karir, aturan pensiun, atau hal normatif lainnya dari dokumen Peraturan Direksi, JANGAN menebak! Anda WAJIB memanggil tool "alat_baca_peraturan" untuk mencari kutipan resminya dari dokumen PDF.
9. Selalu jawab dengan bahasa Indonesia yang profesional.
"""
        
        # Buat SQL Agent
        agent_executor = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="tool-calling",
            verbose=True,
            prefix=custom_prefix,
            handle_parsing_errors=True,
            extra_tools=[alat_rekomendasi_suksesi, alat_analitik_makro, alat_baca_peraturan],
            max_iterations=30,
            max_execution_time=60
        )
        return agent_executor, None
    except Exception as e:
        return None, f"Gagal menginisialisasi sistem: {str(e)}"

def render_chatbot_tab():
    st.markdown("## 🤖 Asisten AI HR (Text-to-SQL)")
    st.markdown("Gunakan asisten ini untuk menanyakan informasi HR dalam bahasa sehari-hari. AI akan menerjemahkannya ke dalam SQL dan memberikan jawaban akurat dari database Anda.")
    
    # Inisialisasi Agent
    agent, error_msg = init_agent()
    
    if error_msg:
        st.error(error_msg)
        st.info("Silakan buka file `.env` di folder proyek dan masukkan API Key Anda.")
        return

    # Inisialisasi riwayat chat di Session State
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Halo! Saya Asisten AI HR. Apa yang ingin Anda ketahui tentang data pegawai, kinerja, atau jabatan?"}
        ]

    # Tampilkan riwayat chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input Chat
    if prompt := st.chat_input("Tanyakan sesuatu (Misal: Siapa saja pegawai dengan box talent Promotable?)"):
        # Tambahkan pertanyaan user ke layar
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Proses jawaban dari AI
        with st.chat_message("assistant"):
            with st.spinner("Sedang menganalisis data SQL..."):
                try:
                    response = agent.invoke({"input": prompt})
                    answer = response.get("output", "Maaf, saya tidak dapat menjawab pertanyaan tersebut.")
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota" in error_str:
                        pesan_kuota = "Mohon maaf kuota AI chatbot hari ini telah habis, Anda bisa mencoba lagi besok."
                        st.error(pesan_kuota)
                        st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ {pesan_kuota}"})
                    else:
                        st.error(f"Terjadi kesalahan saat memproses data: {error_str}")
