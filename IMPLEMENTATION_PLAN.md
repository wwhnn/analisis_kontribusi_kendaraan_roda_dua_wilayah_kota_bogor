# R2 Analytics — Database Implementation (MySQL Online)

## Ringkasan

Aplikasi `app.py` sudah dipindahkan dari dictionary hardcoded `DATA_KEL` ke
database MySQL online (`sql12831186` di `sql12.freesqldatabase.com`), lengkap
dengan fitur CRUD, import CSV, dan export Excel langsung dari Streamlit.

## Skema Database

Dua tabel di database `sql12831186`:

```sql
CREATE TABLE r2_data (
  id INT AUTO_INCREMENT PRIMARY KEY,
  kecamatan VARCHAR(50) NOT NULL,
  kelurahan VARCHAR(50) NOT NULL,
  tahun INT NOT NULL,
  jumlah INT NOT NULL,
  UNIQUE KEY uniq_kk_tahun (kecamatan, kelurahan, tahun)
);

CREATE TABLE kelurahan_geo (
  id INT AUTO_INCREMENT PRIMARY KEY,
  kecamatan VARCHAR(50) NOT NULL,
  kelurahan VARCHAR(50) NOT NULL,
  lat DOUBLE NOT NULL,
  lon DOUBLE NOT NULL,
  UNIQUE KEY uniq_kel (kecamatan, kelurahan)
);
```

`r2_data`: satu baris = jumlah kendaraan R2 di satu kelurahan pada satu tahun.
`kelurahan_geo`: satu baris = titik centroid (lat/lon) satu kelurahan, dipakai
untuk label marker di peta — menggantikan dict `CENTROID_KEL` yang dulu
hardcoded di `app.py`.

## Struktur File

- `db.py` — layer koneksi & query:
  - `get_engine()` — SQLAlchemy engine ke MySQL (`pymysql`), cached via `st.cache_resource`.
  - `init_schema()` — `CREATE TABLE IF NOT EXISTS`.
  - `fetch_all()` — ambil semua baris, cached via `st.cache_data`.
  - `upsert_row(kecamatan, kelurahan, tahun, jumlah)` — insert/update 1 baris.
  - `delete_row(id)` — hapus 1 baris.
  - `delete_by_year(tahun)` — hapus semua baris 1 tahun (dipakai sebelum re-import data riil 1 tahun).
  - `bulk_upsert(df)` — insert/update banyak baris sekaligus (dipakai import CSV & import xlsx).
- `scripts/import_xlsx.py` — **sumber data utama**. Membaca file mentah
  `data/{tahun}.xlsx` (1 baris per kendaraan: `Nopol, Alamat, KR, Kecamatan,
  Kelurahan, ...`), mendeteksi otomatis baris header (posisi & urutan kolom
  berbeda-beda antar file tahun), memfilter `KR == "R2"`, agregasi
  `groupby(Kecamatan, Kelurahan).size()` per tahun, lalu replace data tahun
  tersebut di tabel `r2_data`. Jalankan `python scripts/import_xlsx.py` untuk
  semua tahun, atau `--year 2025` untuk satu tahun saja.
- `scripts/import_centroid.py` — hitung centroid (titik tengah polygon) setiap
  kelurahan otomatis dari `data/Kota_bogor.shp` (`geometry.centroid`), cocokkan
  namanya ke `r2_data` (normalisasi spasi, mis. "BANTARJATI" ↔ "BANTAR JATI"),
  lalu simpan ke tabel `kelurahan_geo`. Dipakai oleh halaman Peta Interaktif
  (`db.fetch_centroid_kel()`) untuk menempatkan label kelurahan — tidak perlu
  lagi koordinat hardcoded di kode.
- `.streamlit/secrets.toml` — kredensial MySQL (**di-gitignore**, jangan pernah commit).
- `.streamlit/secrets.toml.example` — template kosong untuk setup di lingkungan lain.
- `.streamlit/config.toml` — `maxUploadSize = 500` (MB), agar import CSV mentah berukuran besar tidak kena limit kecil seperti di phpMyAdmin.

## Kredensial

Kredensial dibaca dari `st.secrets["mysql"]` (lihat `.streamlit/secrets.toml`):
`host`, `port`, `database`, `user`, `password`. Untuk menjalankan script di luar
Streamlit (`scripts/seed_db.py`), `db.py` tetap membaca file `secrets.toml` yang
sama (atau fallback ke environment variable `MYSQL_HOST`, `MYSQL_PORT`, dst).

## Alur Data di `app.py`

- `load_data()` — query `db.fetch_all()`, bentuk ulang jadi nested dict
  `{kecamatan: {kelurahan: {"r2022":.., "r2023":.., ...}}}` (struktur sama
  seperti `DATA_KEL` sebelumnya) + hitung `TOTAL_KOTA` (sum per tahun) secara
  otomatis. Di-cache dengan `st.cache_data`.
- Variabel module-level `DATA_KEL`, `TOTAL_KOTA`, `KECAMATAN` diisi dari
  `load_data()` saat script dijalankan — seluruh fungsi halaman lain
  (`kec_total`, `build_kec_df`, `build_kel_df`, `load_geodata`, dst) tidak
  berubah karena tetap memakai variabel global ini.
- Tahun masih diasumsikan `[2022, 2023, 2024, 2025]` (`TAHUN_LIST`) karena
  banyak chart men-hardcode 4 tahun ini — menambah tahun baru perlu
  penyesuaian chart terkait, di luar scope perubahan ini.
- Setiap aksi tulis (tambah/edit/hapus/import) memanggil `st.cache_data.clear()`
  lalu `st.rerun()` supaya seluruh dashboard langsung sinkron dengan data baru.

## Halaman "🗄️ Kelola Data"

Ditambahkan ke menu sidebar, berisi 4 tab:

1. **Tambah/Edit** — form pilih/ketik Kecamatan, Kelurahan, Tahun, Jumlah →
   `db.upsert_row`.
2. **Hapus** — pilih baris dari multiselect → `db.delete_row`.
3. **Import CSV** — `st.file_uploader`, mendeteksi otomatis 2 format:
   - *Data ringkasan* (`kecamatan, kelurahan, tahun, jumlah`) → langsung
     `db.bulk_upsert`.
   - *Data mentah/transaksi* (kolom `KR`, `Kecamatan`, `Kelurahan` — seperti
     file pajak kendaraan asli) → filter `KR == "R2"`, agregasi
     `groupby(Kecamatan, Kelurahan).size()`, preview, lalu `db.bulk_upsert`.
     Ini menggantikan upaya upload CSV mentah lewat phpMyAdmin yang gagal
     karena limit ukuran upload 2MB — proses agregasi & insert dilakukan di
     Python/Streamlit yang tidak punya limit kecil seperti itu.
4. **Export Excel** — generate `.xlsx` (pandas `to_excel` + `openpyxl` via
   `io.BytesIO`) dari tabel `r2_data`, dengan filter opsional Kecamatan/Tahun.

## Setup & Menjalankan

```bash
pip install -r requirements.txt

# isi .streamlit/secrets.toml dengan kredensial MySQL (lihat secrets.toml.example)

# import data riil dari file mentah data/2022.xlsx .. data/2025.xlsx
python scripts/import_xlsx.py

# hitung & simpan centroid kelurahan dari shapefile (sekali saja)
python scripts/import_centroid.py

# jalankan aplikasi
streamlit run app.py
```

## Verifikasi yang Sudah Dilakukan

- `scripts/import_xlsx.py` dijalankan untuk 2022–2025: setiap file mentah
  (284k–317k baris) difilter `KR == "R2"` dan diagregasi menjadi 68 baris per
  tahun (272 total). Total R2 per tahun hasil agregasi data riil **cocok
  100%** dengan nilai yang dulu dipakai di aplikasi: 202.745 (2022) /
  201.332 (2023) / 202.089 (2024) / 230.331 (2025) — mengonfirmasi logika
  filter & agregasi benar.
- Semua 9 halaman (`Beranda` s.d. `Tentang`, termasuk `Kelola Data`) dites via
  `streamlit.testing.v1.AppTest` tanpa exception, baik dengan data seed
  maupun setelah diganti data riil dari xlsx.
- Form Tambah/Edit, `upsert_row`, `delete_row`, dan `bulk_upsert` dites
  langsung terhadap MySQL online (insert → verifikasi via `fetch_all` →
  hapus → tabel kembali ke jumlah baris semula).
