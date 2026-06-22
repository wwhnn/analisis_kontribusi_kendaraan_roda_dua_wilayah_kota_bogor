import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

TABLE = "r2_data"
GEO_TABLE = "kelurahan_geo"


def _secret(key: str, default: str = None) -> str:
    try:
        return st.secrets["mysql"][key]
    except Exception:
        return os.environ.get(f"MYSQL_{key.upper()}", default)


@st.cache_resource(show_spinner=False)
def get_engine():
    host = _secret("host")
    port = _secret("port", "3306")
    name = _secret("database")
    user = _secret("user")
    password = _secret("password")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=280)


def init_schema():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kecamatan VARCHAR(50) NOT NULL,
                kelurahan VARCHAR(50) NOT NULL,
                tahun INT NOT NULL,
                jumlah INT NOT NULL,
                UNIQUE KEY uniq_kk_tahun (kecamatan, kelurahan, tahun)
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {GEO_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kecamatan VARCHAR(50) NOT NULL,
                kelurahan VARCHAR(50) NOT NULL,
                lat DOUBLE NOT NULL,
                lon DOUBLE NOT NULL,
                UNIQUE KEY uniq_kel (kecamatan, kelurahan)
            )
        """))


@st.cache_data(show_spinner=False)
def fetch_centroid_kel() -> dict:
    """Return {kelurahan: (lat, lon)} dari tabel kelurahan_geo."""
    engine = get_engine()
    df = pd.read_sql(f"SELECT kelurahan, lat, lon FROM {GEO_TABLE}", engine)
    return {row.kelurahan: (row.lat, row.lon) for row in df.itertuples(index=False)}


def upsert_centroid(kecamatan: str, kelurahan: str, lat: float, lon: float) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {GEO_TABLE} (kecamatan, kelurahan, lat, lon)
            VALUES (:kecamatan, :kelurahan, :lat, :lon)
            ON DUPLICATE KEY UPDATE lat = VALUES(lat), lon = VALUES(lon)
        """), {"kecamatan": kecamatan.strip().upper(), "kelurahan": kelurahan.strip().upper(),
               "lat": float(lat), "lon": float(lon)})


def bulk_upsert_centroid(df: pd.DataFrame) -> int:
    """df harus punya kolom: kecamatan, kelurahan, lat, lon."""
    engine = get_engine()
    rows = [
        {"kecamatan": str(r.kecamatan).strip().upper(),
         "kelurahan": str(r.kelurahan).strip().upper(),
         "lat": float(r.lat), "lon": float(r.lon)}
        for r in df.itertuples(index=False)
    ]
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {GEO_TABLE} (kecamatan, kelurahan, lat, lon)
            VALUES (:kecamatan, :kelurahan, :lat, :lon)
            ON DUPLICATE KEY UPDATE lat = VALUES(lat), lon = VALUES(lon)
        """), rows)
    return len(rows)


@st.cache_data(show_spinner="Memuat data dari database...")
def fetch_all() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(f"SELECT * FROM {TABLE} ORDER BY kecamatan, kelurahan, tahun", engine)


def upsert_row(kecamatan: str, kelurahan: str, tahun: int, jumlah: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {TABLE} (kecamatan, kelurahan, tahun, jumlah)
            VALUES (:kecamatan, :kelurahan, :tahun, :jumlah)
            ON DUPLICATE KEY UPDATE jumlah = VALUES(jumlah)
        """), {"kecamatan": kecamatan.strip().upper(), "kelurahan": kelurahan.strip().upper(),
               "tahun": int(tahun), "jumlah": int(jumlah)})


def delete_row(row_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {TABLE} WHERE id = :id"), {"id": int(row_id)})


def delete_by_year(tahun: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {TABLE} WHERE tahun = :tahun"), {"tahun": int(tahun)})


def bulk_upsert(df: pd.DataFrame) -> int:
    """df harus punya kolom: kecamatan, kelurahan, tahun, jumlah. Return jumlah baris diproses."""
    engine = get_engine()
    rows = [
        {"kecamatan": str(r.kecamatan).strip().upper(),
         "kelurahan": str(r.kelurahan).strip().upper(),
         "tahun": int(r.tahun), "jumlah": int(r.jumlah)}
        for r in df.itertuples(index=False)
    ]
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {TABLE} (kecamatan, kelurahan, tahun, jumlah)
            VALUES (:kecamatan, :kelurahan, :tahun, :jumlah)
            ON DUPLICATE KEY UPDATE jumlah = VALUES(jumlah)
        """), rows)
    return len(rows)
