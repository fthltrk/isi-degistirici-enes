import customtkinter as ctk
import math
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue") 

AYAR_DOSYASI = "parametreler.txt"

# Eksik dosya kontrolü ve otomatik oluşturma
if not os.path.exists(AYAR_DOSYASI):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        f.write("# EGR Cooler Gelişmiş Ayar Dosyası\n")
        f.write("Motor Gücü (P_m) [kW] | 100\n")
        f.write("Egzoz Gazı Debisi (ṁ_e) [kg/s] | 0.15\n")
        f.write("Egzoz Özgül Isısı (C_pe) [J/kgK] | 1150\n")
        f.write("Egzoz Giriş Sıcaklığı (T_ei) [°C] | 500\n")
        f.write("Soğutucu Sıvı Debisi (ṁ_s) [kg/s] | 0.6\n")
        f.write("Soğutucu Özgül Isı (C_ps) [J/kgK] | 3800\n")
        f.write("Soğutucu Giriş Sıcaklığı (T_si) [°C] | 85\n")
        f.write("Isı Transfer Katsayısı (U) [W/m²K] | 250\n")
        f.write("Isı Transfer Alanı (A) [m²] | 1.1025\n")

def ayarlari_oku():
    parametreler = []
    with open(AYAR_DOSYASI, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line and not line.startswith("#"):
                isim, deger = line.split("|")
                parametreler.append({"isim": isim.strip(), "deger": deger.strip()})
    return parametreler

class EGRCoolerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EGR Cooler Termal Analiz Laboratuvarı v2.0")
        self.geometry("1100x820")
        self.resizable(True, True)

        # İleri-Geri (Geçmiş) Hafıza Sistemi Değişkenleri
        self.gecmis_hafiza = []
        self.suanki_indeks = -1

        # Başlık Bölümü
        self.lbl_imza = ctk.CTkLabel(self, text="Bu program Enes Çelik tarafından yapılmıştır.", font=("Arial", 12, "italic"), text_color="#aaaaaa")
        self.lbl_imza.pack(side="top", pady=5)

        # Sekmeli Yapı Oluşturma
        self.tabview = ctk.CTkTabview(self, width=1050, height=740)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_ana = self.tabview.add("Giriş & Hesaplama & Şema")
        self.tab_grafik = self.tabview.add("Grafiksel Analiz Paneli")

        # --- SEKME 1: ANA HESAPLAMA VE GİRİŞLER ---
        # Sol Taraf: Giriş Kutuları
        self.sol_frame = ctk.CTkFrame(self.tab_ana, width=420)
        self.sol_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Sağ Taraf: Sonuçlar, Renk Kodları ve Şema
        self.sag_frame = ctk.CTkFrame(self.tab_ana)
        self.sag_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Motor Tipi Seçimi (Dizel / Benzinli)
        self.lbl_motor = ctk.CTkLabel(self.sol_frame, text="Motor ve Yakıt Tipi Seçimi:", font=("Arial", 12, "bold"))
        self.lbl_motor.pack(pady=(15,2), padx=20, anchor="w")
        
        self.combo_motor = ctk.CTkOptionMenu(self.sol_frame, values=["Dizel Motor Analizi", "Benzinli Motor Analizi"], command=self.motor_tipi_degisti)
        self.combo_motor.pack(pady=5, padx=20, fill="x")

        # İleri / Geri Butonları Paneli
        self.nav_frame = ctk.CTkFrame(self.sol_frame, fg_color="transparent")
        self.nav_frame.pack(pady=5, padx=20, fill="x")
        
        self.btn_geri = ctk.CTkButton(self.nav_frame, text="⬅ Geri (Önceki Veri)", width=100, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=5)
        
        self.btn_ileri = ctk.CTkButton(self.nav_frame, text="İleri (Sonraki) ➡", width=100, command=self.gecmis_ileri, state="disabled")
        self.btn_ileri.pack(side="right", padx=5)

        # Giriş Kutularını Yükleme
        try: self.veriler = ayarlari_oku()
        except: self.veriler = []
        
        self.kutular = []
        for veri in self.veriler:
            entry = self.create_input(self.sol_frame, veri["isim"], veri["deger"])
            self.kutular.append(entry)

        # HESAPLA BUTONU
        self.btn_hesapla = ctk.CTkButton(self.sol_frame, text="HESAPLA (Enter)", font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d", hover_color="#14375e")
        self.btn_hesapla.pack(pady=20, padx=20, fill="x")

        # ENTER TUŞUNU BAĞLAMA (Tüm uygulama genelinde Enter'a basınca çalışır)
        self.bind("<Return>", lambda event: self.hesapla())

        # Şematik Gösterim Alanı (Çizim Tuvali)
        self.lbl_sema_title = ctk.CTkLabel(self.sag_frame, text="EGR Cooler Ters Akış (Counter-Flow) Şematik Gösterimi", font=("Arial", 13, "bold"))
        self.lbl_sema_title.pack(pady=5)
        
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=550, height=180, bg="#1e1e1e", highlightthickness=0)
        self.canvas_sema.pack(pady=5, padx=10, fill="x")
        self.sema_ciz(500, 85, 250, 95) # Başlangıç şeması

        # Sonuç Metin Kutusu ve Renk Barı
        self.txt_sonuc = ctk.CTkTextbox(self.sag_frame, height=200, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10, padx=10, fill="both", expand=True)
        self.txt_sonuc.insert("0.0", "Parametreleri girip HESAPLA butonuna basın veya klavyeden ENTER tuşuna tıklayın.")

        self.renk_bar = ctk.CTkLabel(self.sag_frame, text="Sistem Durumu: Bekleniyor", font=("Arial", 13, "bold"), fg_color="#555555", height=40, text_color="white")
        self.renk_bar.pack(pady=5, padx=10, fill="x")

        # --- SEKME 2: GRAFİKSEL ANALİZ ---
        self.fig, self.axs = plt.subplots(1, 3, figsize=(15, 5))
        self.fig.patch.set_facecolor('#1e1e1e')
        for ax in self.axs:
            ax.set_facecolor('#2d2d2d')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        
        self.canvas_grafik = FigureCanvasTkAgg(self.fig, master=self.tab_grafik)
        self.canvas_grafik.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_input(self, parent, label_text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=2, fill="x", padx=15)
        lbl = ctk.CTkLabel(frame, text=label_text, width=260, anchor="w", font=("Arial", 11, "bold"))
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=110)
        entry.pack(side="right")
        entry.insert(0, default_val)
        return entry

    def motor_tipi_degisti(self, secim):
        # Benzinli araçlarda egzoz giriş sıcaklığı dizellere göre çok daha yüksektir (Genelde 700-900 C)
        # Seçime göre kullanıcıya fikir vermek amaçlı sıcaklık kutusunu otomatik güncelleyelim
        if "Benzinli" in secim:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "750") # Benzinli varsayılanı
        else:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "500") # Dizel varsayılanı

    def sema_ciz(self, T_ei, T_si, T_eo, T_so):
        self.canvas_sema.delete("all")
        # Ana Gövde Borusu
        self.canvas_sema.create_rectangle(100, 50, 450, 130, fill="#333333", outline="#555555", width=2)
        self.canvas_sema.create_text(275, 90, text="EGR GOVDE / ISI DEGISTIRICI", fill="#aaaaaa", font=("Arial", 10, "bold"))

        # EGZOZ GAZI OKU VE GİRİŞ-ÇIKIŞI (Soldan Sağa Akış)
        self.canvas_sema.create_line(30, 70, 100, 70, fill="#ff4444", width=5, arrow="last")
        self.canvas_sema.create_text(65, 50, text=f"Egzoz Giriş\n{T_ei:.1f}°C", fill="#ff6666", font=("Arial", 9, "bold"))
        
        self.canvas_sema.create_line(450, 70, 520, 70, fill="#ff8800", width=5, arrow="last")
        self.canvas_sema.create_text(485, 50, text=f"Egzoz Çıkış\n{T_eo:.1f}°C", fill="#ffaa44", font=("Arial", 9, "bold"))

        # SOĞUTUCU SIVI OKU VE GİRİŞ-ÇIKIŞI (Sağdan Sola - TERS AKIŞ)
        self.canvas_sema.create_line(480, 110, 410, 110, fill="#0088ff", width=4, arrow="last")
        self.canvas_sema.create_text(485, 135, text=f"Sıvı Giriş\n{T_si:.1f}°C", fill="#66bbff", font=("Arial", 9, "bold"))

        self.canvas_sema.create_line(140, 110, 50, 110, fill="#00bb99", width=4, arrow="last")
        self.canvas_sema.create_text(65, 135, text=f"Sıvı Çıkış\n{T_so:.1f}°C", fill="#44ffee", font=("Arial", 9, "bold"))

    def hafizaya_kaydet(self, mevcut_girdiler):
        # Eğer yeni bir hesaplama yapıldıysa ve eskisinden farklıysa geçmiş listesine ekle
        if self.suanki_indeks == -1 or self.gecmis_hafiza[self.suanki_indeks] != mevcut_girdiler:
            # Eğer ortadayken yeni hesap yaptıysa ileriyi kes temizle
            self.gecmis_hafiza = self.gecmis_hafiza[:self.suanki_indeks + 1]
            self.gecmis_hafiza.append(mevcut_girdiler)
            self.suanki_indeks = len(self.gecmis_hafiza) - 1
            self.buton_durumlarini_guncelle()

    def buton_durumlarini_guncelle(self):
        if self.suanki_indeks > 0: self.btn_geri.configure(state="normal")
        else: self.btn_geri.configure(state="disabled")
        
        if self.suanki_indeks < len(self.gecmis_hafiza) - 1: self.btn_ileri.configure(state="normal")
        else: self.btn_ileri.configure(state="disabled")

    def gecmis_veri_yukle(self, indeks):
        girdiler = self.gecmis_hafiza[indeks]
        for i, val in enumerate(girdiler):
            self.kutular[i].delete(0, "end")
            self.kutular[i].insert(0, str(val))
        self.hesapla(hafizaya_yaz=False)

    def gecmis_geri(self):
        if self.suanki_indeks > 0:
            self.suanki_indeks -= 1
            self.gecmis_veri_yukle(self.suanki_indeks)
            self.buton_durumlarini_guncelle()

    def gecmis_ileri(self):
        if self.suanki_indeks < len(self.gecmis_hafiza) - 1:
            self.suanki_indeks += 1
            self.gecmis_veri_yukle(self.suanki_indeks)
            self.buton_durumlarini_guncelle()

    def hesapla(self, hafizaya_yaz=True):
        try:
            # Ekrandaki Değerleri Çekme
            girdiler = [float(k.get()) for k in self.kutular]
            if hafizaya_yaz: self.hafizaya_kaydet(girdiler)

            P_motor, m_dot_e, cp_e, T_e_in, m_dot_s, cp_s, T_s_in, U, A = girdiler
            motor_tipi = self.combo_motor.get()

            # Isı Değiştirici Termal Denklemleri
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
            LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2) if delta_T1 != delta_T2 and delta_T1/delta_T2 > 0 else 0

            # Şemayı Dinamik Olarak Güncelle
            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out)

            # RENK KODLARI VE DURUM SİSTEMİ
            # Egzoz çıkış sıcaklığına göre motor emniyet kontrolü renk tayini
            if T_e_out > 200:
                durum_renk = "#aa2222" # Kırmızı (Tehlikeli Yüksek Sıcaklık)
                durum_mesaj = f"⚠️ KRİTİK DURUM: {motor_tipi} Çıkış Sıcaklığı Çok Yüksek! Soğutma yetersiz."
            elif 120 <= T_e_out <= 200:
                durum_renk = "#22aa55" # Yeşil (Mühendislik Açısından İdeal Bölge)
                durum_mesaj = f"✅ OPTİMUM TASARIM: {motor_tipi} İdeal Isı Transfer Bölgesinde."
            else:
                durum_renk = "#aaaa22" # Sarı (Yoğuşma / Kurum Bağlama Riski)
                durum_mesaj = f"⚠️ UYARI: Sıcaklık çok düşük. Egzoz gazı yoğuşma ve kurumlanma yapabilir."

            self.renk_bar.configure(fg_color=durum_renk, text=durum_mesaj)

            # Sonuç Metnini Yazdır
            sonuc_metni = (
                f"====================================================================\n"
                f" ANALİZ RAPORU TİPİ : {motor_tipi.upper()}\n"
                f"====================================================================\n"
                f" Motor Gücü Başlangıç Değeri  : {P_motor:.2f} kW\n"
                f" Egzoz Gazı Çıkış Sıcaklığı   : {T_e_out:.2f} °C\n"
                f" Soğutma Sıvısı Çıkış Sıcaklığı: {T_s_out:.2f} °C\n"
                f" Gerçekleşen Isı Transferi    : {q/1000:.2f} kW\n"
                f" Cihaz Etkinlik Oranı (Verim) : % {epsilon*100:.2f}\n"
                f" LMTD Değeri                  : {LMTD:.2f} °C\n"
                f" Hesaplanan NTU Boyutsuz Sayısı: {NTU:.4f}\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_metni)

            # --- GRAFİKLERİ ÇİZDİRME (MATPLOTLIB) ---
            for ax in self.axs: ax.clear()

            # Grafik 1: Sıcaklık Değişim Profili
            self.axs[0].plot(["Giriş", "Çıkış"], [T_e_in, T_e_out], 'ro-', label="Egzoz Gazı")
            self.axs[0].plot(["Giriş", "Çıkış"], [T_s_out, T_s_in], 'bo-', label="Soğutucu Sıvı") # Ters Akış Gösterimi
            self.axs[0].set_title("Sıcaklık Değişim Grafiği Profile")
            self.axs[0].set_ylabel("Sıcaklık [°C]")
            self.axs[0].legend()
            self.axs[0].grid(True, linestyle="--", alpha=0.5)

            # Grafik 2: NTU - Sıcaklık Analizi (Alan Genişledikçe Egzoz Çıkış Değişimi)
            ntu_numaralari = [n/10.0 for n in range(1, 40)]
            e_out_grafik = []
            for n_test in ntu_numaralari:
                eps_test = (1 - math.exp(-n_test * (1 - C_r))) / (1 - C_r * math.exp(-n_test * (1 - C_r)))
                q_test = eps_test * q_max
                e_out_grafik.append(T_e_in - (q_test / C_e))
            self.axs[1].plot(ntu_numaralari, e_out_grafik, 'g-', linewidth=2)
            self.axs[1].axvline(x=NTU, color='yellow', linestyle=':', label='Mevcut NTU')
            self.axs[1].set_title("NTU - Çıkış Sıcaklığı Grafiği")
            self.axs[1].set_xlabel("NTU Sayısı")
            self.axs[1].set_ylabel("Egzoz Çıkış Sıcaklığı [°C]")
            self.axs[1].legend()
            self.axs[1].grid(True, linestyle="--", alpha=0.5)

            # Grafik 3: Yüzey Alanı - Transfer Edilen Isı Grafiği
            alanlar = [A * (factor/10.0) for factor in range(1, 25)]
            q_grafik = []
            for a_test in alanlar:
                ntu_t = (U * a_test) / C_min
                eps_t = (1 - math.exp(-ntu_t * (1 - C_r))) / (1 - C_r * math.exp(-ntu_t * (1 - C_r)))
                q_grafik.append((eps_t * q_max) / 1000)
            self.axs[2].plot(alanlar, q_grafik, 'm-', linewidth=2)
            self.axs[2].axvline(x=A, color='cyan', linestyle=':', label='Mevcut Alan')
            self.axs[2].set_title("Yüzey Alanı - Isı Transfer Gücü")
            self.axs[2].set_xlabel("Yüzey Alanı [m²]")
            self.axs[2].set_ylabel("Transfer Edilen Isı [kW]")
            self.axs[2].legend()
            self.axs[2].grid(True, linestyle="--", alpha=0.5)

            self.fig.tight_layout()
            self.canvas_grafik.draw()

        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hata Oluştu! Girdilerin sayısal formatta olduğunu kontrol edin.\nDetay: {str(e)}")

if __name__ == "__main__":
    app = EGRCoolerApp()
    app.mainloop()
