# 📊 Dashboard HRD: Early Warning System & Talent Mapping

Aplikasi dasbor interaktif berbasis **Streamlit** yang dirancang untuk membantu Tim HRD dalam memantau *Early Warning System* (EWS) terkait batas usia pensiun, masa jabatan (kebutuhan rotasi), serta melakukan proyeksi *backup* kandidat untuk perencanaan suksesi (Manajemen Talenta).

Proyek ini dibangun menggunakan data *dummy*/sintetis yang merepresentasikan struktur kepegawaian PT PLN (Persero).

---

## ✨ Fitur Utama

Dasbor ini terbagi menjadi tiga modul utama:

1. **⚠️ EWS Pensiun**
   * Memantau pegawai yang mendekati batas usia pensiun (56 Tahun).
   * Memberikan visibilitas (Radar EWS) untuk pegawai berusia 53 - 55 tahun.
   * Visualisasi komposisi *Dahan Profesi* yang paling terdampak oleh gelombang pensiun terdekat untuk mitigasi *knowledge loss*.

2. **🔄 EWS Masa Jabatan (Kebutuhan Rotasi)**
   * Mengidentifikasi pegawai yang telah menempati jabatan yang sama dalam durasi yang lama untuk mitigasi *stagnancy*.
   * Kategorisasi *Warning* (4-5 Tahun) dan *Kritis* (> 5 Tahun).
   * Menampilkan distribusi masa jabatan (*tenure*) pegawai secara keseluruhan.

3. **🔍 Pencarian Backup Kandidat**
   * *Search engine* sederhana untuk mencari kandidat internal pengisi kekosongan jabatan.
   * Pemfilteran berlapis berdasarkan **Dahan Profesi**, **Level PHDP**, dan **Latar Belakang Pendidikan**.
   * Algoritma pengecualian otomatis: Tidak akan merekomendasikan kandidat yang usianya sudah masuk radar pensiun (> 52 tahun).

---

## 🛠️ Teknologi yang Digunakan

* **Bahasa:** Python 3.8+
* **Framework Web:** [Streamlit](https://streamlit.io/)
* **Manipulasi Data:** Pandas
* **Visualisasi Data:** Plotly Express

---

## 🚀 Panduan Instalasi dan Penggunaan

Ikuti langkah-langkah berikut untuk menjalankan dasbor ini di komputer lokal Anda.

### 1. Prasyarat (*Prerequisites*)
Pastikan Python sudah terinstal di sistem Anda. Direkomendasikan menggunakan *Virtual Environment* (opsional).

### 2. Clone Repositori
```bash
git clone [https://github.com/username-anda/hrd-ews-dashboard.git](https://github.com/username-anda/hrd-ews-dashboard.git)
cd hrd-ews-dashboard
