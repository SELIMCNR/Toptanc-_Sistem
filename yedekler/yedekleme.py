import shutil, datetime, os
from datetime import datetime


def yedekle_veritabani():
    kaynak = "veritabani.db"
    hedef_klasor = "yedekler"
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    hedef_dosya = os.path.join(hedef_klasor, f"yedek_{tarih}.db")

    if not os.path.exists(hedef_klasor):
        os.makedirs(hedef_klasor)

    shutil.copyfile(kaynak, hedef_dosya)
    print(f"Yedek oluşturuldu: {hedef_dosya}")