# R2 Analytics — Implementation Plan

## Ringkasan

Dokumen ini merinci langkah implementasi menambahkan database SQLite dan sistem CRUD ke aplikasi `app.py`, termasuk skrip impor dari file Excel (`2023.xlsx`), lapisan data (SQLAlchemy), antarmuka CRUD di Streamlit, dan instruksi menjalankan.

## Tujuan

- Memindahkan data statis ke database SQLite.
- Menyediakan skrip import dari Excel (pandas + openpyxl).
- Menyediakan API/lapisan data menggunakan SQLAlchemy.
- Menambah UI CRUD di Streamlit untuk `Kecamatan`, `Kelurahan`, dan data jumlah R2 per tahun.
- Menyediakan fitur upload Excel & ekspor CSV.

## Asumsi

- Workspace root: aplikasi dijalankan dari folder ini (ada `app.py`).
- File Excel contoh: `2023.xlsx` tersedia (kolom minimal: `Kecamatan`, `Kelurahan`, `Tahun`, `Jumlah`).
- Target DB: SQLite (`data/r2_kota_bogor.db`).

## Teknologi & Dependensi

- Python 3.10+
- Streamlit
- pandas
- openpyxl
- SQLAlchemy
- alembic (opsional untuk migrasi)
- geopandas (opsional, jika ada shapefile)

Update `requirements.txt` menambahkan bila perlu:

```
pandas
openpyxl
SQLAlchemy
alembic
geopandas
```

## Database Schema (SQLite)

Tabel utama:

- `kecamatan`
  - `id` INTEGER PRIMARY KEY
  - `nama` TEXT UNIQUE NOT NULL
  - `centroid_lat` REAL
  - `centroid_lon` REAL
- `kelurahan`
  - `id` INTEGER PRIMARY KEY
  - `kecamatan_id` INTEGER REFERENCES kecamatan(id) ON DELETE CASCADE
  - `nama` TEXT NOT NULL
- `r2_counts`
  - `id` INTEGER PRIMARY KEY
  - `kelurahan_id` INTEGER REFERENCES kelurahan(id) ON DELETE CASCADE
  - `tahun` INTEGER NOT NULL
  - `jumlah` INTEGER NOT NULL
  - UNIQUE(kelurahan_id, tahun)

Contoh SQL (SQLite):

```sql
CREATE TABLE kecamatan (
  id INTEGER PRIMARY KEY,
  nama TEXT UNIQUE NOT NULL,
  centroid_lat REAL,
  centroid_lon REAL
);
CREATE TABLE kelurahan (
  id INTEGER PRIMARY KEY,
  kecamatan_id INTEGER NOT NULL,
  nama TEXT NOT NULL,
  FOREIGN KEY(kecamatan_id) REFERENCES kecamatan(id) ON DELETE CASCADE
);
CREATE TABLE r2_counts (
  id INTEGER PRIMARY KEY,
  kelurahan_id INTEGER NOT NULL,
  tahun INTEGER NOT NULL,
  jumlah INTEGER NOT NULL,
  UNIQUE(kelurahan_id, tahun),
  FOREIGN KEY(kelurahan_id) REFERENCES kelurahan(id) ON DELETE CASCADE
);
```

## SQLAlchemy Models (sketsa)

- `Kecamatan` model
- `Kelurahan` model (relationship ke Kecamatan)
- `R2Count` model (relationship ke Kelurahan)

Simpan model di `models.py`.

## Skrip Inisialisasi DB

File: `scripts/init_db.py`

- Membuat folder `data/` jika belum ada.
- Membuat file DB `data/r2_kota_bogor.db` jika belum ada.
- Menginisialisasi schema (SQLAlchemy `Base.metadata.create_all(engine)`).
- Menyediakan opsi `--seed` untuk memasukkan geojson fallback + centroid dari `app.py`.

Contoh run:

```bash
python scripts/init_db.py --seed
```

## Skrip Import Excel

File: `scripts/import_excel.py`

- Argumen: `--file 2023.xlsx`, `--sheet` (opsional), `--year` (opsional).
- Baca dengan `pandas.read_excel(..., engine='openpyxl')`.
- Harus melakukan normalisasi nama (strip, upper) untuk mencocokkan `Kecamatan` & `Kelurahan`.
- Untuk setiap baris: pastikan `Kecamatan` ada di tabel kecamatan (insert jika tidak), pastikan `Kelurahan` ada (hubungkan ke kecamatan), lalu insert/update `r2_counts` untuk `tahun`.
- Mode `--dry-run` untuk preview.

Contoh run:

```bash
python scripts/import_excel.py --file data/2023.xlsx
```

## Refactor `app.py` (lapisan data)

- Tambahkan modul `db.py` untuk koordinasi engine dan session maker.
- Ganti konstanta `DATA_KEL`, `TOTAL_KOTA`, dsb. dengan fungsi pembacaan dari DB:
  - `get_kecamatan_summary(year)` mengembalikan ringkasan per kecamatan
  - `get_kelurahan_list(kecamatan=None)` mengembalikan dataframe kelurahan
  - `get_geojson_from_shapefile()` tetap dipertahankan, namun fallback baca dari DB jika tersedia
- Gunakan caching (`@st.cache_data`) di layer baca DB untuk performa.

## UI CRUD di Streamlit

Halaman baru/sektion di sidebar: "🛠️ Admin Data"
Fitur:

- Tampilkan tabel `kecamatan` dengan tombol `Edit` dan `Delete`.
- Form `Tambah Kecamatan` (nama, centroid lat/lon).
- Untuk `Kelurahan`: filter by kecamatan, list kelurahan, form tambah/edit/delete.
- Untuk `R2Counts`: form tambah/edit (pilih kecamatan -> kelurahan -> tahun -> jumlah), juga opsi bulk-import via Excel.
- Semua operasi melakukan commit ke DB menggunakan SQLAlchemy session.

Contoh fungsi:

- `create_kecamatan(name, lat=None, lon=None)`
- `update_kecamatan(id, **fields)`
- `delete_kecamatan(id)`
- `create_kelurahan(kecamatan_id, name)`
- `upsert_r2count(kelurahan_id, tahun, jumlah)`

## Upload/Import & Ekspor

- Upload Excel: gunakan `st.file_uploader` dan jalankan routine import dari `pandas.DataFrame` serupa `scripts/import_excel.py`.
- Ekspor CSV: tombol `st.download_button` untuk mengekspor hasil query (kecamatan/kelurahan/r2_counts).

## Update Peta & Analisis

- Ubah fungsi load_geodata dan pembentukan `geojson` agar atribut `r2`, `persen`, `tumbuh` dihitung dari DB (agg per kecamatan/kelurahan).
- Tetap gunakan `GEOJSON_FALLBACK` bila shapefile tidak tersedia.

## Migrasi dan Seed

- Simpel: `scripts/init_db.py --seed` untuk seed dari `GEOJSON_FALLBACK` dan `DATA_KEL` jika diperlukan.
- Opsional: gunakan `alembic` untuk migrasi skema lebih lanjut.

## Struktur File yang Disarankan

- `app.py` (refactor agar import dari `db.py` & `models.py`)
- `models.py` (SQLAlchemy models)
- `db.py` (engine/session)
- `scripts/init_db.py` (inisialisasi + seed)
- `scripts/import_excel.py` (import Excel ke DB)
- `data/r2_kota_bogor.db` (SQLite DB)
- `IMPLEMENTATION_PLAN.md` (this file)

## Testing & Validasi

- Skrip unit test minimal di `tests/test_import.py` — validasi parsing Excel dan insert ke DB (sqlite-memory).
- Manual test: import `data/2023.xlsx`, jalankan `streamlit run app.py`, cek halaman Admin CRUD, Peta dan Analisis menampilkan data baru.

## Perintah Cepat

- Inisialisasi DB & seed:

```bash
python scripts/init_db.py --seed
```

- Import Excel:

```bash
python scripts/import_excel.py --file data/2023.xlsx
```

- Jalankan streamlit:

```bash
streamlit run app.py
```

## Checklist Implementasi (mapping ke TODO)

- [ ] `scripts/init_db.py` + models (`models.py`, `db.py`)
- [ ] `scripts/import_excel.py`
- [ ] Refactor `app.py` untuk membaca DB
- [ ] Streamlit Admin CRUD
- [ ] Upload/Export fitur
- [ ] Tests dan README

---

Jika Anda setuju, saya bisa langsung mulai membuat file `models.py`, `db.py`, dan `scripts/init_db.py` selanjutnya mengimplementasikan skrip import `scripts/import_excel.py`.
