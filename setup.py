# file: setup.py (Diperbarui untuk PostgreSQL)

import psycopg2
import bcrypt
from datetime import datetime
from pathlib import Path
import sys

current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from app.core import config
except ImportError:
    print("❌ Gagal mengimpor konfigurasi.")
    sys.exit(1)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def setup_database():
    try:
        if not config.DATABASE_URL:
            print("❌ DATABASE_URL tidak ditemukan di file .env. Proses setup dibatalkan.")
            return False
            
        print(f"🚀 Mencoba terhubung ke database PostgreSQL...")
        conn = psycopg2.connect(config.DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Berhasil terhubung.")
        
        print("⚠️  Menghapus tabel lama (jika ada)...")
        cursor.execute('DROP TABLE IF EXISTS chat_history, documents, users CASCADE;')
        
        print("🏗️  Membuat struktur tabel baru...")
        cursor.execute('''
        CREATE TABLE users (
            username VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(256) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP NOT NULL
        );
        ''')
        cursor.execute('''
        CREATE TABLE documents (
            id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(255) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TIMESTAMP NOT NULL,
            file_size BIGINT,
            is_indexed BOOLEAN NOT NULL DEFAULT false
        );
        ''')
        cursor.execute('''
        CREATE TABLE chat_history (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            username VARCHAR(255) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            document_ids JSONB
        );
        CREATE INDEX idx_chat_history_session_id ON chat_history (session_id);
        ''')
        
        print("🔑 Membuat akun admin default...")
        admin_pass = hash_password(config.DEFAULT_ADMIN_PASSWORD) 
        cursor.execute(
            "INSERT INTO users (username, email, password, role, created_at) VALUES (%s, %s, %s, %s, %s)",
            ('admin_unnes', 'admin@mail.unnes.ac.id', admin_pass, 'admin', datetime.now())
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Setup database selesai dengan sukses!")
        return True

    except Exception as e:
        print(f"\n❌ GAGAL melakukan setup database: {e}")
        return False

if __name__ == "__main__":
    setup_database()