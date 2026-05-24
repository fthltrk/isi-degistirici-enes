import customtkinter as ctk
import math
import os

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue") 

# AYARLAR DOSYASININ ADI
AYAR_DOSYASI = "parametreler.txt"

# Eğer bilgisayarda bu dosya yoksa, varsayılan değerlerle otomatik oluştursun
if not os.path.exists(AYAR_DOSYASI):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        f.write("# EGR Cooler Programi Ayar Dosyasi\n")
        f.write("# Esittir (=) işaretinden sonraki değerleri değiştirip kaydedebilirsiniz.\n\n")
        f.write("Motor Gucu (kW) = 100\n")
        f.write("Egzoz Gazisi Kutlesel Debisi (kg/s) = 0.15\n")
        f.write("Egzoz Gazisi Ozgul Isisi (J/kgK) = 1150\n")
        f.write("Egzoz Gazisi Giris Sicakligi (C) = 500\n")
        f.write("Sogutma Sivisi Kutlesel Debisi (kg/s) = 0.6\n")
        f.write("Sogutma Sivisi Ozgul Isisi (J/kgK) = 3800\n")
        f.write("Sogutma Sivisi Giris Sicakligi (C) = 85\n")
        f.write("Toplam Isi Transfer Katsayisi (U) = 250\n")
        f.write("Toplam Isi Transfer Alani (A) = 1.1025\n")

def ayarlari_oku():
    """Metin dosyasındaki değerleri okuyan fonksiyon"""
    ayarlar = {}
    with open(AYAR_DOSYASI, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                anahtar, deger = line.split("=")
                ayarlar[anahtar.strip()] = deger.strip()
    return ayarlar

class EGRCoolerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EGR Cooler Performans Analizi")
        self.geometry("550x750")
        self.resizable(False, False)

        self.lbl_baslik = ctk.CTkLabel(self, text="EGR Cooler Giriş Parametreleri", font=("Arial", 18, "bold"))
        self.lbl_baslik.pack(pady=15)

        # Ayarları dosyadan yükle
        try:
            self.veriler = ayarlari_oku()
        except:
            self.veriler = {}

        # GİRİŞ ALANLARI VE ETİKETLERİ (Değerler dosyadan geliyor)
        self.entry_P_motor = self.create_input("Motor Gücü (P_motor) [kW]:", self.veriler.get("Motor Gucu (kW)", "100"))
        self.entry_m_dot_e = self.create_input("Egzoz Gazı Kütlesel Debisi (m_dot_e) [kg/s]:", self.veriler.get("Egzoz Gazisi Kutlesel Debisi (kg/s)", "0.15"))
        self.entry_cp_e = self.create_input("Egzoz Gazı Özgül Isısı (cp_e) [J/kgK]:", self.veriler.get("Egzoz Gazisi Ozgul Isisi (J/kgK)", "1150"))
        self.entry_T_e_in = self.create_input("Egzoz Gazı Giriş Sıcaklığı (T_e_in) [°C]:", self.veriler.get("Egzoz Gazisi Giris Sicakligi (C)", "500"))
        
        self.entry_m_dot_s = self.create_input("Soğutma Sıvısı Kütlesel Debisi (m_dot_s) [kg/s]:", self.veriler.get("Sogutma Sivisi Kutlesel Debisi (kg/s)", "0.6"))
        self.entry_cp_s = self.create_input("Soğutma Sıvısı Özgül Isısı (cp_s) [J/kgK]:", self.veriler.get("Sogutma Sivisi Ozgul Isisi (J/kgK)", "3800"))
        self.entry_T_s_in = self.create_input("Soğutma Sıvısı Giriş Sıcaklığı (T_s_in) [°C]:", self.veriler.get("Sogutma Sivisi Giris Sicakligi (C)", "85"))
        
        self.entry_U = self.create_input("Toplam Isı Transfer Katsayısı (U) [W/m^2K]:", self.veriler.get("Toplam Isi Transfer Katsayisi (U)", "250"))
        self.entry_A = self.create_input("Toplam Isı Transfer Alanı (A) [m^2]:", self.veriler.get("Toplam Isi Transfer Alani (A)", "1.1025"))

        # HESAPLA BUTONU
        self.btn_hesapla = ctk.CTkButton(self, text="HESAPLA", font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d", hover_color="#14375e")
        self.btn_hesapla.pack(pady=15)

        # SONUÇ ALANI
        self.txt_sonuc = ctk.CTkTextbox(self, width=500, height=180, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10)
        self.txt_sonuc.insert("0.0", "Değerleri girip HESAPLA butonuna basın.")

    def create_input(self, label_text, default_val):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=3, fill="x", px=25)
        lbl = ctk.CTkLabel(frame, text=label_text, width=320, anchor="w", font=("Arial", 11, "bold"))
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=150)
        entry.pack(side="right")
        entry.insert(0, default_val)
        return entry

    def hesapla(self):
        try:
            P_motor = float(self.entry_P_motor.get())
            m_dot_e = float(self.entry_m_dot_e.get())
            cp_e = float(self.entry_cp_e.get())
            T_e_in = float(self.entry_T_e_in.get())
            m_dot_s = float(self.entry_m_dot_s.get())
            cp_s = float(self.entry_cp_s.get())
            T_s_in = float(self.entry_T_s_in.get())
            U = float(self.entry_U.get())
            A = float(self.entry_A.get())

            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
            
            NTU = (U * A) / C_min
            epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r)))
            
            q_max = C_min * (T_e_in - T_s_in)
            q = epsilon * q_max
            
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            delta_T1 = T_e_in - T_s_out
            delta_T2 = T_e_out - T_s_in
            
            if delta_T1 / delta_T2 > 0 and delta_T1 != delta_T2:
                LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)
                q_LMTD = U * A * LMTD
            else:
                LMTD = 0
                q_LMTD = 0

            sonuc_metni = (
                f"===================================================\n"
                f" Giriş Motor Gücü             : {P_motor:.2f} kW\n"
                f"===================================================\n"
                f" Egzoz Gazı Çıkış Sıcaklığı    : {T_e_out:6.2f} °C\n"
                f" Soğutma Suyu Çıkış Sıcaklığı  : {T_s_out:6.2f} °C\n"
                f" Transfer Edilen Isı (e-NTU)   : {q/1000:6.2f} kW\n"
                f" Transfer Edilen Isı (LMTD)    : {q_LMTD/1000:6.2f} kW\n"
                f" Cihaz Etkinliği (Verimi)       : % {epsilon*100:.2f}\n"
                f" NTU Değeri                    : {NTU:6.2f}\n"
                f" LMTD Değeri                   : {LMTD:6.2f} °C\n"
                f"==================================================="
            )
            
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_metni)

        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hata: Girdileri kontrol edin!\n{str(e)}")

if __name__ == "__main__":
    app = EGRCoolerApp()
    app.mainloop()
