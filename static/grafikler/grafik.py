import sqlite3, matplotlib.pyplot as plt, os
import matplotlib
matplotlib.use('Agg')  # GUI olmayan backend

def borc_grafigi(baslangic=None, bitis=None):
    # Grafik klasörünü oluştur
    klasor = os.path.join("static", "grafikler")
    os.makedirs(klasor, exist_ok=True)

    # Veritabanı bağlantısı
    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    # SQL sorgusu: tarih aralığı varsa filtrele
    if baslangic and bitis:
        cursor.execute("""
            SELECT t.ad, IFNULL(SUM(o.tutar), 0) AS toplam_odeme
            FROM toptancilar t
            LEFT JOIN odemeler o ON t.id = o.toptanci_id
            WHERE o.tarih BETWEEN ? AND ?
            GROUP BY t.id
        """, (baslangic, bitis))
    else:
        cursor.execute("""
            SELECT t.ad, IFNULL(SUM(o.tutar), 0) AS toplam_odeme
            FROM toptancilar t
            LEFT JOIN odemeler o ON t.id = o.toptanci_id
            GROUP BY t.id
        """)

    veriler = cursor.fetchall()
    conn.close()

    if not veriler:
        print("Grafik için veri yok.")
        return

    isimler = [x[0] for x in veriler]
    borclar = [x[1] for x in veriler]

    # Grafik çizimi
    plt.figure(figsize=(10, 6))
    plt.bar(isimler, borclar, color='orange')
    plt.title("Toptancı Borç Durumu")
    plt.xlabel("Toptancılar")
    plt.ylabel("Toplam Ödeme (₺)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Dosya kaydı
    dosya_yolu = os.path.join(klasor, "borc_grafigi.png")
    plt.savefig(dosya_yolu)
    plt.close()
    print("Grafik başarıyla oluşturuldu:", dosya_yolu)
    print("Veri:", veriler)

# Doğrudan çalıştırıldığında tüm veriye göre grafik üret
if __name__ == "__main__":
    borc_grafigi()