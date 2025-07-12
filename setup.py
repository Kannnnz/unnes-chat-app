# file: setup.py

import psycopg2
import sys
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from app.core import config
    from app.core.security import get_password_hash
except ImportError as e:
    print(f"❌ Gagal mengimpor modul: {e}. Pastikan file app/core/config.py dan app/core/security.py ada.")
    sys.exit(1)

def setup_database():
    try:
        print("🚀 Mencoba terhubung ke database PostgreSQL...")
        conn = psycopg2.connect(config.DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Berhasil terhubung.")
        
        print("⚠️  Menghapus tabel lama (jika ada)...")
        cursor.execute('DROP TABLE IF EXISTS chat_history, documents, users CASCADE;')
        
        print("🏗️  Membuat struktur tabel baru...")
        cursor.execute('''
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(256),
            role VARCHAR(50) NOT NULL DEFAULT 'user',
            is_google_user BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        ''')
        cursor.execute('''
        CREATE TABLE documents (
            id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(255) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            file_size BIGINT,
            is_indexed BOOLEAN NOT NULL DEFAULT FALSE
        );
        ''')
        cursor.execute('''
        CREATE TABLE chat_history (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            username VARCHAR(255) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            document_ids JSONB
        );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history (session_id);')
        
        print("🔑 Membuat akun admin default...")
        admin_pass_hash = get_password_hash(config.DEFAULT_ADMIN_PASSWORD)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            ('admin_unnes', 'admin@mail.unnes.ac.id', admin_pass_hash, 'admin')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Setup database selesai dengan sukses!")
        return True
    except Exception as e:
        print(f"\n❌ GAGAL melakukan setup database: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    setup_database()
