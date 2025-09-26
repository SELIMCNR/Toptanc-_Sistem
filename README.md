Tabii Selim! Aşağıda “Toptanc-_Sistem” adlı projen için sade, profesyonel ve işlevsel bir `README.md` taslağı hazırladım. Bu dosya hem GitHub’da hem Render gibi deploy platformlarında net bir tanıtım sağlar:

---

## 📦 Toptanc-_Sistem – Stok ve Borç Takip Otomasyonu

**Toptanc-_Sistem**, küçük ve orta ölçekli işletmeler için geliştirilmiş bir Python tabanlı otomasyon sistemidir. Ürün ekleme, satış, müşteri borç takibi, barkod arama, Excel/PDF raporlama ve canlı müzik/haber entegrasyonu gibi özellikler sunar.

---

### 🚀 Özellikler

- 🛒 Ürün ekleme, düzenleme, barkodla arama  
- 💰 Satış ekranı ve borçlandırma modülü  
- 📊 Borç raporu ve grafik analizi  
- 📤 Excel ve PDF dışa aktarma  
- 🔍 Barkod ile ürün detay görüntüleme  
- 🎵 Arka planda müzik oynatma (karışık ve atlamalı)  
- 🌐 Canlı döviz, hava durumu ve haber paneli  
- 🧩 Modüler yapı: `add_product.py`, `sales_screen.py`, `customer_gui.py` vs.

---

### 🛠️ Kurulum

```bash
git clone https://github.com/kullaniciadi/Toptanc-_Sistem.git
cd Toptanc-_Sistem
pip install -r requirements.txt
python main.py
```

---

### 📁 Klasör Yapısı

```
Toptanc-_Sistem/
├── main.py
├── müzikler/              # Arka plan müzikleri (.mp3)
├── database.py            # SQLite veritabanı kurulumu
├── customer_database.py   # Müşteri tabloları
├── add_product.py         # Ürün ekleme ekranı
├── sales_screen.py        # Satış ekranı
├── customer_gui.py        # Müşteri işlemleri
├── export_to_excel.py     # Excel dışa aktarma
├── export_debt_to_pdf.py  # PDF borç raporu
├── ...
```

---

### 📦 Gereksinimler

- Python 3.10+
- Tkinter
- Pygame
- Requests
- ReportLab
- OpenPyXL

---

### 🌐 Canlı Yayınlama (Opsiyonel)

Projeyi ücretsiz olarak [Render](https://render.com), [Replit](https://replit.com) veya [PythonAnywhere](https://www.pythonanywhere.com) üzerinden yayınlayabilirsiniz.

---

### 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

---
