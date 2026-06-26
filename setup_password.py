"""
setup_password.py
=================
Jalankan script ini SEKALI untuk:
1. Generate password hash dari password pilihanmu
2. Cetak isi yang harus dimasukkan ke Streamlit Secrets

Cara pakai:
    python setup_password.py

Lalu copy output-nya ke:
    - Streamlit Cloud → App Settings → Secrets
    - atau .streamlit/secrets.toml (lokal)
"""

import hashlib
import hmac
import os
import secrets
import sys


def make_hash(plain_password: str, salt: str) -> str:
    return hmac.new(
        salt.encode("utf-8"),
        plain_password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def main():
    print("=" * 55)
    print("  Setup Password Admin – R2 Analytics Kota Bogor")
    print("=" * 55)
    print()

    # Minta password dari user
    import getpass
    while True:
        pwd1 = getpass.getpass("Masukkan password admin baru: ")
        if len(pwd1) < 8:
            print("❌ Password minimal 8 karakter.")
            continue
        pwd2 = getpass.getpass("Konfirmasi password: ")
        if pwd1 != pwd2:
            print("❌ Password tidak cocok, ulangi.")
            continue
        break

    # Generate salt random
    salt = secrets.token_hex(32)

    # Generate hash
    hashed = make_hash(pwd1, salt)

    print()
    print("=" * 55)
    print("✅ Berhasil! Copy teks berikut ke Streamlit Secrets:")
    print("=" * 55)
    print()
    print("[auth]")
    print(f'salt          = "{salt}"')
    print(f'password_hash = "{hashed}"')
    print()
    print("=" * 55)
    print("Cara tambahkan ke Streamlit Cloud:")
    print("  1. Buka https://share.streamlit.io")
    print("  2. Klik ⋮ (titik tiga) di app kamu → Settings")
    print("  3. Tab 'Secrets' → paste teks di atas → Save")
    print()
    print("Cara tambahkan ke lokal (.streamlit/secrets.toml):")
    print("  1. Buat folder .streamlit/ di root project")
    print("  2. Buat file secrets.toml")
    print("  3. Paste teks di atas ke dalamnya")
    print("=" * 55)


if __name__ == "__main__":
    main()
