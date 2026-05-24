import customtkinter as ctk
import math

# Görsel Temayı Ayarla
ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue") 

class EGRCoolerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Ayarları
        self.title("EGR Cooler Performans Analizi")
        self.geometry("450x650")
        self.resizable(False, False)

        # --- BAŞLIK ---
        self.lbl_baslik = ctk.CTkLabel(self, text="EGR Cooler Giriş Parametreleri", font=("Arial", 18, "bold"))
        self.lbl_baslik.pack(pady=15)

        # --- GİRİŞ ALANLARI (MATLAB'daki Sabitleriniz) ---
        self.entry_m_dot_e = self.create_input("Egzoz Kütlesel Debi (m_dot_e) [kg/s]", "0.15")
        self.entry_cp_e = self.create_input("Egzoz Özgül Isı (cp_e) [J/kgK]", "1150")
        self.entry_T_e_in = self.create_input("Egzoz Giriş Sıcaklığı (T_e_in) [°C]", "500")
        
        self.entry_m_dot_s = self.create_input("Soğutucu Sıvı Debi (m_dot_s) [kg/s]", "0.6")
        self.entry_cp_s = self.create_input("Soğutucu Özgül Isı (cp_s) [J/kgK]", "3800")
        self.entry_T_s_in = self.create_input("Soğutucu Giriş Sıcaklığı (T_s_in) [°C]", "85")
        
        self.entry_U = self.create_input("Isı Transfer Katsayısı (U) [W/m^2K]", "250")
        self.entry_A = self.create_input("Isı Transfer Alanı (A) [m^2]", "1.1025")

        # --- HESAPLA BUTONU ---
        self.btn_hesapla = ctk.CTkButton(self, text="HESAPLA", font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d", hover_color="#14375e")
        self.btn_hesapla.pack(pady=20)

        # --- SONUÇ ALANI (Çıktılar İçin Büyük Metin Kutusu) ---
        self.txt_sonuc = ctk.CTkTextbox(self, width=400, height=180, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10)
        self.txt_sonuc.insert("0.0", "Değerleri girip HESAPLA butonuna basın.")

    def create_input(self, placeholder, default_val):
        """Giriş kutularını pratik oluşturmak için yardımcı fonksiyon"""
        entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=380)
        entry.pack(pady=4)
        entry.insert(0, default_val) # Varsayılan değerleri kutulara yazar
        return entry

    def hesapla(self):
        try:
            # 1. Arayüzden Verileri Çekme
            m_dot_e = float(self.entry_m_dot_e.get())
            cp_e = float(self.entry_cp_e.get())
            T_e_in = float(self.entry_T_e_in.get())
            
            m_dot_s = float(self.entry_m_dot_s.get())
            cp_s = float(self.entry_cp_s.get())
            T_s_in = float(self.entry_T_s_in.get())
            
            U = float(self.entry_U.get())
            A = float(self.entry_A.get())

            # 2. e-NTU Yöntemi Hesaplamaları (MATLAB Kodunuzun Aynısı)
            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
            
            NTU = (U * A) / C_min
            
            # Etkinlik (Zıt Akışlı)
            epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r)))
            
            q_max = C_min * (T_e_in - T_s_in)
            q = epsilon * q_max
            
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            # 3. LMTD Yöntemi ile Sağlama
            delta_T1 = T_e_in - T_s_out
            delta_T2 = T_e_out - T_s_in
            
            # Logaritma hatasını engellemek için kontrol
            if delta_T1 / delta_T2 > 0 and delta_T1 != delta_T2:
                LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)
                q_LMTD = U * A * LMTD
            else:
                LMTD = 0
                q_LMTD = 0

            # 4. Sonuçları Arayüzdeki Kutuya Yazdırma
            sonuc_metni = (
                f"=========================================\n"
                f"       EGR COOLER PERFORMANS SONUÇLARI   \n"
                f"=========================================\n"
                f"Egzoz Gazı Çıkış Sıcaklığı : {T_e_out:6.2f} °C\n"
                f"Soğutma Suyu Çıkış Sıcaklığı : {T_s_out:6.2f} °C\n"
                f"Transfer Edilen Isı (e-NTU) : {q/1000:6.2f} kW\n"
                f"Transfer Edilen Isı (LMTD)  : {q_LMTD/1000:6.2f} kW\n"
                f"Cihaz Etkinliği (Verimi)    : % {epsilon*100:.2f}\n"
                f"NTU Değeri                  : {NTU:6.2f}\n"
                f"LMTD Değeri                 : {LMTD:6.2f} °C\n"
                f"========================================="
            )
            
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_metni)

        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hata: Lütfen girdileri kontrol edin!\n{str(e)}")

if __name__ == "__main__":
    app = EGRCoolerApp()
    app.mainloop()
