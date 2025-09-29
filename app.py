from flask import Flask, render_template, request, redirect,session
from apscheduler.schedulers.background import BackgroundScheduler
from yedekler.yedekleme import yedekle_veritabani
from static.grafikler.grafik import borc_grafigi
import sqlite3, hashlib
from fpdf import FPDF
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf.csrf import CSRFProtect

from flask import Flask, render_template, request, redirect, session, flash
app = Flask(__name__)

app.secret_key = 'gizli-anahtar'
#csrf = CSRFProtect(app)
# Zamanlayıcı
scheduler = BackgroundScheduler()
scheduler.add_job(yedekle_veritabani, 'cron', hour=23, minute=59)
scheduler.start()

from flask import Response
from fpdf import FPDF
import os
from datetime import datetime
@app.route('/rapor-pdf')
def rapor_pdf():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.ad AS toptanci_adi,
       IFNULL(SUM(u.fiyat * u.adet), 0) AS toplam_borc,
       IFNULL(SUM(o.tutar), 0) AS toplam_odeme,
       MAX(IFNULL(SUM(u.fiyat * u.adet), 0) - IFNULL(SUM(o.tutar), 0), 0) AS kalan
FROM toptancilar t
LEFT JOIN urunler u ON t.id = u.toptanci_id
LEFT JOIN odemeler o ON t.id = o.toptanci_id
GROUP BY t.id
ORDER BY t.ad
    """)
    veriler = cursor.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()

    font_yolu = os.path.join("fonts", "DejaVuSans.ttf")
    pdf.add_font('DejaVu', '', font_yolu, uni=True)
    pdf.set_font('DejaVu', '', 12)

    pdf.cell(200, 10, txt="Aksu Mobil - Toptancı Borç Raporu", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    if veriler:
        pdf.cell(60, 10, txt="Toptancı", border=1)
        pdf.cell(40, 10, txt="Borç", border=1)
        pdf.cell(40, 10, txt="Ödeme", border=1)
        pdf.cell(40, 10, txt="Kalan", border=1)
        pdf.ln()

        for toptanci, borc, odeme, kalan in veriler:
            pdf.cell(60, 10, txt=str(toptanci), border=1)
            pdf.cell(40, 10, txt=f"{borc:.2f}", border=1)
            pdf.cell(40, 10, txt=f"{odeme:.2f}", border=1)
            pdf.cell(40, 10, txt=f"{kalan:.2f}", border=1)
            pdf.ln()
    else:
        pdf.cell(200, 10, txt="Kayıt bulunamadı.", ln=True)

    response = Response(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename=borc_raporu.pdf'
    return response

@app.route('/odeme-listesi')
def odeme_listesi():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id, t.ad, o.tarih, o.tutar, o.odeme_yontemi
        FROM odemeler o
        JOIN toptancilar t ON o.toptanci_id = t.id
        ORDER BY o.tarih DESC
    """)
    odemeler_raw = cursor.fetchall()

    odemeler = []
    for odeme in odemeler_raw:
        odeme_id, toptanci_ad, tarih, tutar, yontem = odeme

        cursor.execute("""
            SELECT u.ad, ou.adet
            FROM odeme_urunleri ou
            JOIN urunler u ON ou.urun_id = u.id
            WHERE ou.odeme_id = ?
        """, (odeme_id,))
        urunler = cursor.fetchall()
        urun_text = ", ".join([f"{u[0]} x{u[1]}" for u in urunler]) if urunler else "—"

        odemeler.append((odeme_id, toptanci_ad, tarih, tutar, yontem, urun_text))

    conn.close()
    return render_template("odeme_listesi.html", odemeler=odemeler)
    
from flask import Flask, render_template, request, redirect, session
import sqlite3

@app.route('/toptanci-listesi')
def toptanci_listesi():
    if 'kullanici' not in session:
        return redirect('/giris')

    arama = request.args.get('arama', '')
    with sqlite3.connect("veritabani.db") as conn:
        cursor = conn.cursor()
        if arama:
            cursor.execute("""
                SELECT id, ad, telefon, borc, odenen, (borc - odenen) AS kalan
                FROM toptancilar
                WHERE ad LIKE ?
            """, ('%' + arama + '%',))
        else:
            cursor.execute("""
                SELECT id, ad, telefon, borc, odenen, (borc - odenen) AS kalan
                FROM toptancilar
            """)
        toptancilar = cursor.fetchall()

    return render_template("toptanci_listesi.html", toptancilar=toptancilar, arama=arama)


@app.route('/toptanci-sil', methods=['POST'])
def toptanci_sil():
    if 'kullanici' not in session:
        return redirect('/giris')

    try:
        id = int(request.form.get('id', 0))
        if id <= 0:
            flash("Geçersiz toptancı ID", "danger")
            return redirect('/toptanci-listesi')

        with sqlite3.connect("veritabani.db") as conn:
            cursor = conn.cursor()

            # Ödeme kontrolü
            cursor.execute("SELECT COUNT(*) FROM odemeler WHERE toptanci_id=?", (id,))
            sayi = cursor.fetchone()[0]
            if sayi > 0:
                flash("Bu toptancıya ait ödeme kayıtları var. Önce onları silin.", "warning")
                return redirect('/toptanci-listesi')

            # Silme işlemi
            cursor.execute("DELETE FROM toptancilar WHERE id=?", (id,))
            silinen = cursor.rowcount
            conn.commit()

            if silinen == 0:
                flash("Silme başarısız: Toptancı bulunamadı.", "danger")
            else:
                flash("Toptancı başarıyla silindi.", "success")

    except ValueError:
        flash("Geçersiz ID formatı.", "danger")
    except Exception as e:
        flash(f"Hata oluştu: {str(e)}", "danger")

    return redirect('/toptanci-listesi')

@app.route('/toptanci-duzenle/<int:id>', methods=['GET', 'POST'])
def toptanci_duzenle(id):
    if 'kullanici' not in session:
        return redirect('/giris')

    try:
        with sqlite3.connect("veritabani.db") as conn:
            cursor = conn.cursor()

            if request.method == 'POST':
                ad = request.form.get('ad', '').strip()
                telefon = request.form.get('telefon', '').strip()
                borc = float(request.form.get('borc', '0').replace(',', '.'))
                odenen = float(request.form.get('odenen', '0').replace(',', '.'))

                cursor.execute("""
                    UPDATE toptancilar
                    SET ad = ?, telefon = ?, borc = ?, odenen = ?
                    WHERE id = ?
                """, (ad, telefon, borc, odenen, id))
                conn.commit()
                flash("Toptancı bilgileri güncellendi", "success")
                return redirect('/toptanci-listesi')

            cursor.execute("SELECT id, ad, telefon, borc, odenen FROM toptancilar WHERE id = ?", (id,))
            toptanci = cursor.fetchone()

            if not toptanci:
                flash("Toptancı bulunamadı", "danger")
                return redirect('/toptanci-listesi')

            borc = float(toptanci[3])
            odenen = float(toptanci[4])
            kalan = borc - odenen
            return render_template("toptanci_duzenle.html", toptanci=toptanci, kalan=kalan)

    except ValueError:
        flash("Borç ve ödenen alanlarına geçerli sayısal değer girin.", "danger")
        return redirect(f"/toptanci-duzenle/{id}")

    except Exception as e:
        flash(f"Hata oluştu: {str(e)}", "danger")
        return redirect('/toptanci-listesi')

@app.route('/rapor')
def rapor():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        t.id,
        t.ad AS toptanci_adi,
        IFNULL(SUM(u.fiyat * u.adet), 0) AS toplam_borc,
        IFNULL(SUM(o.tutar), 0) AS toplam_odeme,
        MAX(IFNULL(SUM(u.fiyat * u.adet), 0) - IFNULL(SUM(o.tutar), 0), 0) AS kalan
    FROM toptancilar t
    LEFT JOIN urunler u ON t.id = u.toptanci_id
    LEFT JOIN odemeler o ON t.id = o.toptanci_id
    GROUP BY t.id
    ORDER BY t.ad
""")
    raporlar = cursor.fetchall()
    print("Raporlar:", raporlar)
    conn.close()

    return render_template("rapor.html", raporlar=raporlar)
@app.route('/rapor-detay/<int:toptanci_id>', methods=['GET', 'POST'])
def rapor_detay(toptanci_id):
    if 'kullanici' not in session:
        return redirect('/giris')

    baslangic = request.form.get('baslangic')
    bitis = request.form.get('bitis')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    query = """
        SELECT u.ad AS urun_adi,
               u.fiyat,
               u.adet,
               (u.fiyat * u.adet) AS borc,
               IFNULL(SUM(o.tutar), 0) AS odeme,
               MAX((u.fiyat * u.adet) - IFNULL(SUM(o.tutar), 0), 0) AS kalan
        FROM urunler u
        LEFT JOIN odemeler o ON u.toptanci_id = o.toptanci_id
        WHERE u.toptanci_id = ?
    """
    params = [toptanci_id]

    if baslangic and bitis:
        query += " AND o.tarih BETWEEN ? AND ?"
        params.extend([baslangic, bitis])

    query += " GROUP BY u.id"
    cursor.execute(query, params)
    detaylar = cursor.fetchall()

    cursor.execute("SELECT ad FROM toptancilar WHERE id = ?", (toptanci_id,))
    toptanci_adi = cursor.fetchone()[0]
    conn.close()

    return render_template("rapor_detay.html", detaylar=detaylar, toptanci=toptanci_adi, toptanci_id=toptanci_id)
from urllib.parse import quote

@app.route('/rapor-detay-pdf/<int:toptanci_id>')
def rapor_detay_pdf(toptanci_id):
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.ad AS urun_adi,
               u.fiyat,
               u.adet,
               (u.fiyat * u.adet) AS borc,
               IFNULL(SUM(o.tutar), 0) AS odeme,
               MAX((u.fiyat * u.adet) - IFNULL(SUM(o.tutar), 0), 0) AS kalan
        FROM urunler u
        LEFT JOIN odemeler o ON u.toptanci_id = o.toptanci_id
        WHERE u.toptanci_id = ?
        GROUP BY u.id
    """, (toptanci_id,))
    detaylar = cursor.fetchall()

    cursor.execute("SELECT ad FROM toptancilar WHERE id = ?", (toptanci_id,))
    toptanci_adi = cursor.fetchone()[0]
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    font_yolu = os.path.join("fonts", "DejaVuSans.ttf")
    pdf.add_font('DejaVu', '', font_yolu, uni=True)
    pdf.set_font('DejaVu', '', 12)

    pdf.cell(200, 10, txt=f"{toptanci_adi} - Ürün Bazlı Borç Raporu", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    if detaylar:
        pdf.cell(40, 10, txt="Ürün", border=1)
        pdf.cell(25, 10, txt="Fiyat", border=1)
        pdf.cell(20, 10, txt="Adet", border=1)
        pdf.cell(30, 10, txt="Borç", border=1)
        pdf.cell(30, 10, txt="Ödeme", border=1)
        pdf.cell(30, 10, txt="Kalan", border=1)
        pdf.ln()

        for urun, fiyat, adet, borc, odeme, kalan in detaylar:
            pdf.cell(40, 10, txt=str(urun), border=1)
            pdf.cell(25, 10, txt=f"{fiyat:.2f}", border=1)
            pdf.cell(20, 10, txt=str(adet), border=1)
            pdf.cell(30, 10, txt=f"{borc:.2f}", border=1)
            pdf.cell(30, 10, txt=f"{odeme:.2f}", border=1)
            pdf.cell(30, 10, txt=f"{kalan:.2f}", border=1)
            pdf.ln()
    else:
        pdf.cell(200, 10, txt="Kayıt bulunamadı.", ln=True)

    response = Response(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
   
    safe_filename = quote(f"{toptanci_adi}_detay_raporu.pdf")
    response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{safe_filename}" 
    return response
import bcrypt

def sifrele(parola: str) -> str:
    """
    Verilen düz metin parolayı bcrypt ile güvenli şekilde şifreler.
    Her çağrıda farklı tuz kullanılır, bu yüzden çıktılar benzersiz olur.
    """
    salt = bcrypt.gensalt(rounds=12)  # rounds artırılırsa daha güvenli ama daha yavaş olur
    hashed = bcrypt.hashpw(parola.encode('utf-8'), salt)
    return hashed.decode('utf-8')
from flask import request, redirect, render_template, session
import sqlite3
import hashlib

def dogrula_sha256(girilen, kayitli_hash):
    return hashlib.sha256(girilen.encode('utf-8')).hexdigest() == kayitli_hash

from flask import render_template, request, redirect, session, flash

import sqlite3

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi', '').strip()
        girilen_sifre = request.form.get('sifre', '').strip()

        if not kullanici_adi or not girilen_sifre:
            flash("Kullanıcı adı ve parola boş olamaz", "danger")
            return redirect('/giris')

        try:
            conn = sqlite3.connect("veritabani.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, sifre, yetki FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
            sonuc = cursor.fetchone()
            conn.close()

            if sonuc:
                kullanici_id, kayitli_hash, yetki = sonuc

                if dogrula_sha256(girilen_sifre, kayitli_hash):
                    session['kullanici'] = kullanici_adi
                    session['yetki'] = yetki

                    flash("Giriş başarılı", "success")
                    return redirect('/admin' if yetki == 'admin' else '/')
                else:
                    flash("Parola hatalı", "danger")
            else:
                flash("Kullanıcı bulunamadı", "danger")

        except Exception as e:
            flash(f"Hata oluştu: {str(e)}", "danger")

    return render_template("giris.html") 
@app.route('/odeme-duzenle/<int:id>', methods=['GET', 'POST'])
def odeme_duzenle(id):
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        tarih = request.form['tarih']
        tutar = float(request.form['tutar'])
        yontem = request.form['odeme_yontemi']

        cursor.execute("UPDATE odemeler SET tarih=?, tutar=?, odeme_yontemi=? WHERE id=?",
                       (tarih, tutar, yontem, id))
        conn.commit()
        conn.close()
        return redirect('/odeme-listesi')

    cursor.execute("SELECT tarih, tutar, odeme_yontemi FROM odemeler WHERE id=?", (id,))
    odeme = cursor.fetchone()
    conn.close()
    return render_template("odeme_duzenle.html", odeme=odeme, id=id)
@app.route('/odeme-sil/<int:id>')
def odeme_sil(id):
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM odemeler WHERE id=?", (id,))
    cursor.execute("DELETE FROM odeme_urunleri WHERE odeme_id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/odeme-listesi')
@app.route('/urun-ekle', methods=['GET', 'POST'])
def urun_ekle():
 
    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        ad = request.form['ad']
        fiyat = float(request.form['fiyat'])
        adet = int(request.form['adet'])
        toptanci_id = int(request.form['toptanci_id'])

        cursor.execute("INSERT INTO urunler (ad, fiyat, adet, toptanci_id) VALUES (?, ?, ?, ?)",
                       (ad, fiyat, adet, toptanci_id))
        conn.commit()
        conn.close()
        
        return redirect('/urun-listesi')

    cursor.execute("SELECT id, ad FROM toptancilar")
    toptancilar = cursor.fetchall()
    conn.close()
    return render_template("urun_ekle.html", toptancilar=toptancilar)


@app.route('/urun-listesi')
def urun_listesi():
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.ad, u.fiyat, u.adet, t.ad
        FROM urunler u
        JOIN toptancilar t ON u.toptanci_id = t.id
        ORDER BY t.ad
    """)
    urunler = cursor.fetchall()
    conn.close()

    return render_template("urun_listesi.html", urunler=urunler)

@app.route('/urun-duzenle/<int:id>', methods=['GET', 'POST'])
def urun_duzenle(id):
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        ad = request.form['ad']
        fiyat = float(request.form['fiyat'])
        adet = int(request.form['adet'])
        toptanci_id = int(request.form['toptanci_id'])

        cursor.execute("UPDATE urunler SET ad=?, fiyat=?, adet=?, toptanci_id=? WHERE id=?",
                       (ad, fiyat, adet, toptanci_id, id))
        conn.commit()
        conn.close()
        return redirect('/urun-listesi')

    cursor.execute("SELECT ad, fiyat, adet, toptanci_id FROM urunler WHERE id=?", (id,))
    urun = cursor.fetchone()

    cursor.execute("SELECT id, ad FROM toptancilar")
    toptancilar = cursor.fetchall()
    conn.close()

    return render_template("urun_duzenle.html", urun=urun, toptancilar=toptancilar, id=id)
@app.route('/urun-sil/<int:id>')
def urun_sil(id):
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM urunler WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/urun-listesi')
@app.route('/toptanci-ekle', methods=['GET', 'POST'])
def toptanci_ekle():
    if 'kullanici' not in session:
        return redirect('/giris')

    if request.method == 'POST':
        try:
            ad = request.form.get('ad', '').strip()
            telefon = request.form.get('telefon', '').strip()
            borc = float(request.form.get('borc', '0').replace(',', '.'))
            odenen = float(request.form.get('odenen', '0').replace(',', '.'))
            kalan = borc - odenen

            if not ad or not telefon:
                flash("Ad ve telefon alanları zorunludur.", "danger")
                return redirect('/toptanci-ekle')

            with sqlite3.connect("veritabani.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO toptancilar (ad, telefon, borc, odenen, kalan)
                    VALUES (?, ?, ?, ?, ?)
                """, (ad, telefon, borc, odenen, kalan))
                conn.commit()

            flash("Yeni toptancı başarıyla eklendi.", "success")
            return redirect('/toptanci-listesi')

        except ValueError:
            flash("Borç ve ödenen alanlarına geçerli sayısal değer girin.", "danger")
        except Exception as e:
            flash(f"Hata oluştu: {str(e)}", "danger")

    return render_template("toptanci_ekle.html")


@app.route('/odeme-ekle', methods=['GET', 'POST'])
def odeme_ekle():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        toptanci_id = int(request.form['toptanci_id'])
        tarih = request.form['tarih']
        tutar = float(request.form['tutar'])
        yontem = request.form['odeme_yontemi']

        cursor.execute("INSERT INTO odemeler (toptanci_id, tarih, tutar, odeme_yontemi) VALUES (?, ?, ?, ?)",
                       (toptanci_id, tarih, tutar, yontem))
        odeme_id = cursor.lastrowid

        # Seçilen ürünleri bağla
        urunler = request.form.getlist('urun_id')
        adetler = request.form.getlist('adet')
        for uid, adet in zip(urunler, adetler):
            if int(adet) > 0:
                cursor.execute("INSERT INTO odeme_urunleri (odeme_id, urun_id, adet) VALUES (?, ?, ?)",
                               (odeme_id, int(uid), int(adet)))

        conn.commit()
        conn.close()
        return redirect('/odeme-listesi')

    cursor.execute("SELECT id, ad FROM toptancilar")
    toptancilar = cursor.fetchall()

    cursor.execute("SELECT id, ad FROM urunler")
    urunler = cursor.fetchall()

    conn.close()
    return render_template("odeme_ekle.html", toptancilar=toptancilar, urunler=urunler)

from flask import Response

@app.route('/toptanci-export')
def toptanci_export():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, ad, telefon FROM toptancilar")
    rows = cursor.fetchall()
    conn.close()

    def generate():
        yield 'ID,Ad,Telefon\n'
        for row in rows:
            yield ','.join(map(str, row)) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=toptancilar.csv"})
    
@app.route('/odeme-export')
def odeme_export():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.id, t.ad, o.tarih, o.tutar, o.odeme_yontemi
        FROM odemeler o
        JOIN toptancilar t ON o.toptanci_id = t.id
        ORDER BY o.tarih DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    def generate():
        yield 'ID,Toptancı,Tarih,Tutar,Yöntem\n'
        for row in rows:
            yield ','.join(map(str, row)) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=odemeler.csv"})    
@app.route('/')
def index():
    if 'kullanici' not in session:
        return redirect('/giris')

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM toptancilar")
    toptanci_sayisi = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(SUM(tutar), 0) FROM odemeler")
    toplam_odeme = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(tarih) FROM odemeler")
    son_odeme_tarihi = cursor.fetchone()[0]

    conn.close()

    return render_template("index.html", toptanci_sayisi=toptanci_sayisi,
                           toplam_odeme=toplam_odeme,
                           son_odeme_tarihi=son_odeme_tarihi)
@app.route('/admin')
def admin_panel():
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return "Bu sayfaya erişim yetkiniz yok."

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM toptancilar")
    toptanci_sayisi = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(SUM(tutar), 0) FROM odemeler")
    toplam_odeme = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(tarih) FROM odemeler")
    son_odeme_tarihi = cursor.fetchone()[0]

    cursor.execute("""
        SELECT t.ad, SUM(o.tutar) AS toplam
        FROM odemeler o
        JOIN toptancilar t ON o.toptanci_id = t.id
        GROUP BY t.id
        ORDER BY toplam DESC
        LIMIT 1
    """)
    en_aktif = cursor.fetchone()
    en_aktif = en_aktif[0] if en_aktif else "Yok"

    cursor.execute("""
        SELECT o.id, t.ad, o.tarih, o.tutar, o.odeme_yontemi
        FROM odemeler o
        JOIN toptancilar t ON o.toptanci_id = t.id
        ORDER BY o.tarih DESC
        LIMIT 10
    """)
    odemeler = cursor.fetchall()

    conn.close()

    return render_template("admin.html",
                           toptanci_sayisi=toptanci_sayisi,
                           toplam_odeme=toplam_odeme,
                           son_odeme_tarihi=son_odeme_tarihi,
                           en_aktif=en_aktif,
                           odemeler=odemeler)

@app.route('/kullanici-ekle', methods=['GET', 'POST'])
def kullanici_ekle():

        if 'kullanici' not in session or session.get('yetki') != 'admin':
            return "Bu sayfaya erişim yetkiniz yok."

        if request.method == 'POST':
            kullanici_adi = request.form['kullanici_adi']
            sifre = sifrele(request.form['sifre'])  # Şifreleme fonksiyonun varsa
            yetki = request.form['yetki']

            conn = sqlite3.connect("veritabani.db")
            cursor = conn.cursor()

            # Aynı kullanıcı adı var mı kontrolü
            cursor.execute("SELECT COUNT(*) FROM kullanicilar WHERE kullanici_adi=?", (kullanici_adi,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return "Bu kullanıcı adı zaten kayıtlı."

            cursor.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, yetki) VALUES (?, ?, ?)",
                        (kullanici_adi, sifre, yetki))
            conn.commit()
            conn.close()
            return redirect('/admin')

        return render_template("kullanici_ekle.html") 

@app.route('/kullanici-listesi')
def kullanici_listesi():
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return "Bu sayfaya erişim yetkiniz yok."

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, kullanici_adi, yetki FROM kullanicilar")
    kullanicilar = cursor.fetchall()
    conn.close()

    return render_template("kullanici_listesi.html", kullanicilar=kullanicilar)
@app.route('/sifre-sifirla/<int:id>', methods=['GET', 'POST'])
def sifre_sifirla(id):
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return "Bu sayfaya erişim yetkiniz yok."

    if request.method == 'POST':
        yeni_sifre = sifrele(request.form['sifre'])
        conn = sqlite3.connect("veritabani.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE kullanicilar SET sifre=? WHERE id=?", (yeni_sifre, id))
        conn.commit()
        conn.close()
        return redirect('/kullanici-listesi')

    return render_template("sifre_sifirla.html", id=id)
@app.route('/yetki-degistir/<int:id>', methods=['GET', 'POST'])
def yetki_degistir(id):
    if 'kullanici' not in session or session.get('yetki') != 'admin':
        return "Bu sayfaya erişim yetkiniz yok."

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        yeni_yetki = request.form['yetki']
        cursor.execute("UPDATE kullanicilar SET yetki=? WHERE id=?", (yeni_yetki, id))
        conn.commit()
        conn.close()
        return redirect('/kullanici-listesi')

    cursor.execute("SELECT kullanici_adi, yetki FROM kullanicilar WHERE id=?", (id,))
    kullanici = cursor.fetchone()
    conn.close()
    return render_template("yetki_degistir.html", kullanici=kullanici, id=id)
@app.route('/cikis')
def cikis():
    session.clear()
    return redirect('/giris')
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)