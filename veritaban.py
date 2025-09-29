import sqlite3

conn = sqlite3.connect("veritabani.db")
cursor = conn.cursor()

id = 6
cursor.execute("DELETE FROM toptancilar WHERE id=?", (id,))
print("Silinen:", cursor.rowcount)

conn.commit()
conn.close()