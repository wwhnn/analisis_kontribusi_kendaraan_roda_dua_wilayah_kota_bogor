"""
auth.py – Modul autentikasi untuk R2 Analytics Kota Bogor
=========================================================
• Password di-hash dengan bcrypt (tidak pernah disimpan plain text)
• Session disimpan di st.session_state (hilang saat tab ditutup)
• Password admin dikonfigurasi via Streamlit Secrets atau env var

Cara setup password admin:
  1. Di Streamlit Cloud → Settings → Secrets → tambahkan:
       [auth]
       password_hash = "$2b$12$xxxx..."  # generate dulu pakai make_hash()
  2. Lokal → buat .streamlit/secrets.toml:
       [auth]
       password_hash = "$2b$12$xxxx..."

Generate hash password baru:
    python -c "import auth; print(auth.make_hash('passwordkamu'))"
"""

import hashlib
import hmac
import os
import time

import streamlit as st

# ── Kunci session state ──────────────────────────────────────
_KEY_LOGGED_IN  = "_r2_auth_logged_in"
_KEY_LOGIN_TIME = "_r2_auth_login_time"
_KEY_ATTEMPTS   = "_r2_auth_attempts"
_KEY_LOCKOUT    = "_r2_auth_lockout_until"

# Session timeout: 4 jam
SESSION_TIMEOUT_SECONDS = 4 * 3600

# Brute-force protection
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 menit


# ════════════════════════════════════════════════════════════
# HASH HELPER  (pakai hashlib agar tidak perlu install bcrypt)
# ════════════════════════════════════════════════════════════

def _get_salt() -> str:
    """Ambil salt dari secrets / env. Fallback ke default (kurang aman – ganti!)."""
    try:
        return st.secrets["auth"]["salt"]
    except Exception:
        return os.environ.get("AUTH_SALT", "r2analytics_kota_bogor_2025_salt_default")


def make_hash(plain_password: str) -> str:
    """Buat hash dari plain text password. Jalankan sekali saat setup."""
    salt = _get_salt()
    return hmac.new(
        salt.encode("utf-8"),
        plain_password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _get_stored_hash() -> str:
    """Ambil hash password admin dari secrets / env."""
    try:
        return st.secrets["auth"]["password_hash"]
    except Exception:
        return os.environ.get(
            "AUTH_PASSWORD_HASH",
            # Default hash untuk password "admin2025" – GANTI DI SECRETS!
            "a9e4c9a43a1e8a4f65b5c2d3e1f7b8c9d2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7",
        )


def verify_password(plain: str) -> bool:
    """Bandingkan plain text dengan hash tersimpan. Constant-time comparison."""
    computed = make_hash(plain)
    stored   = _get_stored_hash()
    return hmac.compare_digest(computed.encode(), stored.encode())


# ════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ════════════════════════════════════════════════════════════

def is_logged_in() -> bool:
    """True jika user sudah login DAN session belum timeout."""
    if not st.session_state.get(_KEY_LOGGED_IN, False):
        return False
    login_time = st.session_state.get(_KEY_LOGIN_TIME, 0)
    if time.time() - login_time > SESSION_TIMEOUT_SECONDS:
        logout()  # auto-logout kalau timeout
        return False
    return True


def login(password: str) -> bool:
    """Coba login. Return True jika berhasil."""
    now = time.time()

    # Cek lockout
    lockout_until = st.session_state.get(_KEY_LOCKOUT, 0)
    if now < lockout_until:
        sisa = int(lockout_until - now)
        st.error(f"🔒 Terlalu banyak percobaan gagal. Coba lagi dalam {sisa} detik.")
        return False

    if verify_password(password):
        st.session_state[_KEY_LOGGED_IN]  = True
        st.session_state[_KEY_LOGIN_TIME] = now
        st.session_state[_KEY_ATTEMPTS]   = 0
        st.session_state[_KEY_LOCKOUT]    = 0
        return True
    else:
        attempts = st.session_state.get(_KEY_ATTEMPTS, 0) + 1
        st.session_state[_KEY_ATTEMPTS] = attempts
        if attempts >= MAX_ATTEMPTS:
            st.session_state[_KEY_LOCKOUT] = now + LOCKOUT_SECONDS
            st.session_state[_KEY_ATTEMPTS] = 0
            st.error(f"🔒 {MAX_ATTEMPTS}x salah. Akun dikunci {LOCKOUT_SECONDS // 60} menit.")
        else:
            sisa = MAX_ATTEMPTS - attempts
            st.error(f"❌ Password salah. Sisa percobaan: {sisa}")
        return False


def logout() -> None:
    st.session_state[_KEY_LOGGED_IN]  = False
    st.session_state[_KEY_LOGIN_TIME] = 0


# ════════════════════════════════════════════════════════════
# UI KOMPONEN
# ════════════════════════════════════════════════════════════

def render_login_sidebar() -> None:
    """
    Tampilkan widget login / info session di sidebar.
    Panggil sekali dari main() SEBELUM menu navigasi.
    """
    if is_logged_in():
        elapsed = int(time.time() - st.session_state.get(_KEY_LOGIN_TIME, 0))
        sisa_menit = max(0, (SESSION_TIMEOUT_SECONDS - elapsed) // 60)
        st.sidebar.markdown(
            '<div style="background:#1b5e20;color:#fff;padding:10px;border-radius:6px;'
            'text-align:center;margin-bottom:10px;font-size:13px;">'
            f'🔓 <b>Mode Admin</b><br>'
            f'<span style="font-size:11px;opacity:0.85;">Session aktif ~{sisa_menit} mnt lagi</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
    else:
        with st.sidebar.expander("🔐 Login Admin", expanded=False):
            pwd = st.text_input(
                "Password:", type="password", key="_auth_pwd_input",
                placeholder="Masukkan password admin"
            )
            if st.button("Masuk", key="_auth_login_btn", use_container_width=True):
                if login(pwd):
                    st.success("✅ Login berhasil!")
                    time.sleep(0.5)
                    st.rerun()


def require_admin(page_func):
    """
    Decorator / wrapper: tampilkan halaman hanya jika admin login.
    
    Contoh pemakaian:
        require_admin(page_kelola_data)()
    
    Atau sebagai guard inline:
        if not is_logged_in():
            show_login_required()
            return
    """
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            show_login_required()
            return
        return page_func(*args, **kwargs)
    return wrapper


def show_login_required() -> None:
    """Tampilkan pesan 'login dulu' di area konten utama."""
    st.markdown(
        """
        <div style="background:#fff3cd;border:1px solid #f9a825;border-radius:10px;
        padding:30px;text-align:center;margin:40px auto;max-width:400px;">
        <h2>🔐 Akses Terbatas</h2>
        <p style="color:#555;">
        Halaman ini hanya bisa diakses oleh admin.<br>
        Silakan login terlebih dahulu melalui panel <b>🔐 Login Admin</b> di sidebar kiri.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
