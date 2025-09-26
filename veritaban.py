import sqlite3

conn = sqlite3.connect("veritabani.db")
cursor = conn.cursor()

# Kullanıcı tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT UNIQUE NOT NULL,
    sifre TEXT NOT NULL
)
""")

cursor.execute("""
          ALTER TABLE kullanicilar ADD COLUMN yetki TEXT DEFAULT 'kullanici';     
               """)
# Toptancı tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS toptancilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL,
    telefon TEXT
)
""")

# Ödeme tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS odemeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    toptanci_id INTEGER,
    tarih DATE,
    tutar REAL,
    odeme_yontemi TEXT,
    FOREIGN KEY (toptanci_id) REFERENCES toptancilar(id)
)
""")

conn.commit()
conn.close()
print("Veritabanı başarıyla oluşturuldu.")