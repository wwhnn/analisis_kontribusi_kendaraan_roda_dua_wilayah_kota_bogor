"""Hitung centroid (titik tengah) setiap kelurahan otomatis dari shapefile
data/Kota_bogor.shp dan simpan ke tabel kelurahan_geo di MySQL — menggantikan
dict CENTROID_KEL yang dulu hardcoded di app.py.

Nama kelurahan di shapefile (kolom DESA) kadang beda spasi dengan nama di
database r2_data (mis. "BANTARJATI" vs "BANTAR JATI"), jadi dicocokkan
dengan menormalisasi spasi (uppercase + hapus spasi) dulu.

Jalankan:
    python scripts/import_centroid.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
import pandas as pd
import db

SHP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Kota_bogor.shp")


def norm(s: str) -> str:
    return str(s).strip().upper().replace(" ", "")


def main():
    db.init_schema()
    df_r2 = db.fetch_all.__wrapped__()
    nama_resmi = {norm(k): k for k in df_r2["kelurahan"].unique()}
    kec_resmi = {norm(k): k for k in df_r2["kecamatan"].unique()}

    gdf = gpd.read_file(SHP_PATH)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    rows = []
    tidak_cocok = []
    for _, r in gdf.iterrows():
        key = norm(r["DESA"])
        if key not in nama_resmi:
            tidak_cocok.append(r["DESA"])
            continue
        centroid = r.geometry.centroid
        rows.append({
            "kecamatan": kec_resmi.get(norm(r["KECAMATAN"]), r["KECAMATAN"]),
            "kelurahan": nama_resmi[key],
            "lat": centroid.y,
            "lon": centroid.x,
        })

    if tidak_cocok:
        print("Tidak cocok dengan data r2_data (dilewati):", tidak_cocok)

    df_geo = pd.DataFrame(rows)
    n = db.bulk_upsert_centroid(df_geo)
    print(f"{n} centroid kelurahan disimpan ke tabel '{db.GEO_TABLE}'.")


if __name__ == "__main__":
    main()
