"""Import data riil R2 dari file mentah data/{tahun}.xlsx ke tabel r2_data di MySQL.

File mentah berisi 1 baris per kendaraan dengan kolom:
Nopol, Alamat, KR, Kd JENIS, Kecamatan, Kelurahan, Tg Akhir Pajak, Tg akhir STNK.
Script ini memfilter KR == "R2", lalu menghitung jumlah per Kecamatan+Kelurahan
per tahun, dan menggantikan (bukan menambah) data tahun tersebut di database.

Jalankan:
    python scripts/import_xlsx.py                # import semua tahun yang ada filenya
    python scripts/import_xlsx.py --year 2025     # import tahun tertentu saja
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import db

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
YEARS = [2022, 2023, 2024, 2025]


def _read_with_header_detection(path: str) -> pd.DataFrame:
    """Header tidak selalu di baris pertama (beberapa file punya baris kosong
    di awal) dan urutan kolom berbeda antar tahun, jadi deteksi baris header
    dengan mencari sel 'Nopol' di antara 5 baris pertama."""
    raw = pd.read_excel(path, engine="openpyxl", header=None, nrows=5)
    header_idx = None
    for i in range(len(raw)):
        if raw.iloc[i].astype(str).str.strip().eq("Nopol").any():
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Baris header 'Nopol' tidak ditemukan di {path}")
    return pd.read_excel(path, engine="openpyxl", header=header_idx)


def aggregate_year(tahun: int) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{tahun}.xlsx")
    print(f"[{tahun}] membaca {path} ...")
    df = _read_with_header_detection(path)

    df["KR"] = df["KR"].astype(str).str.strip().str.upper()
    df_r2 = df[df["KR"] == "R2"].copy()
    df_r2["Kecamatan"] = df_r2["Kecamatan"].astype(str).str.strip().str.upper()
    df_r2["Kelurahan"] = df_r2["Kelurahan"].astype(str).str.strip().str.upper()

    agg = (df_r2.groupby(["Kecamatan", "Kelurahan"]).size()
           .reset_index(name="jumlah"))
    agg["tahun"] = tahun
    agg = agg.rename(columns={"Kecamatan": "kecamatan", "Kelurahan": "kelurahan"})

    print(f"[{tahun}] total baris: {len(df):,} | R2: {len(df_r2):,} | "
          f"baris agregat: {len(agg)} | kecamatan: {agg['kecamatan'].nunique()} | "
          f"kelurahan: {agg['kelurahan'].nunique()}")
    return agg[["kecamatan", "kelurahan", "tahun", "jumlah"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None, help="Import hanya tahun ini")
    args = parser.parse_args()

    years = [args.year] if args.year else YEARS
    db.init_schema()

    for tahun in years:
        path = os.path.join(DATA_DIR, f"{tahun}.xlsx")
        if not os.path.exists(path):
            print(f"[{tahun}] dilewati, file tidak ditemukan: {path}")
            continue
        agg = aggregate_year(tahun)
        db.delete_by_year(tahun)
        n = db.bulk_upsert(agg)
        print(f"[{tahun}] {n} baris dimasukkan ke database.\n")

    print("Selesai.")


if __name__ == "__main__":
    main()
