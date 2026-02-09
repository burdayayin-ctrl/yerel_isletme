"""
YEREL İŞLETME STRATEJİ MOTORU - PROFESYONEL SÜRÜM
Geliştirici: Uzman Yazılım Ekibi
Versiyon: 2.0.0
Tarih: 2024
Lisans: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import json
import threading
import queue
import time
from datetime import datetime
import sys
from pathlib import Path

# Bağımlılık kontrolü
try:
    import torch
    from transformers import pipeline, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    pipeline = None
    AutoTokenizer = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    FPDF = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

# Konfigürasyon
CONFIG = {
    'version': '2.0.0',
    'default_language': 'TR',
    'supported_languages': ['TR', 'EN', 'DE', 'FR'],
    'max_history': 50,
    'auto_save_interval': 300,  # 5 dakika
    'default_theme': 'light',
    'export_formats': ['txt', 'pdf', 'json', 'html']
}

# Sektör Veritabanı (Genişletilmiş)
INDUSTRY_DATABASE = {
    "çiçekçi": {
        "analysis": "hızlı, görsel, özel gün odaklı, duygusal bağ önemli",
        "chain": ["düğün salonu", "fotoğrafçı", "pastane", "organizasyon"],
        "tone": "Samimi, romantik, duygusal",
        "keywords": ["buket", "aranjman", "saksı", "doğum günü", "düğün"],
        "seasonal": ["sevgililer günü", "anneler günü", "yılbaşı"]
    },
    "kuaför": {
        "analysis": "yorum tabanlı, tekrar müşteri odaklı, görsel portfolyo kritik",
        "chain": ["gelinlikçi", "makyaj", "estetik", "güzellik salonu"],
        "tone": "Güven verici, profesyonel, trend",
        "keywords": ["saç kesimi", "boya", "styling", "bakım"],
        "seasonal": ["düğün sezonu", "bayram", "yaz öncesi"]
    },
    "restoran": {
        "analysis": "lokasyon, puan, menü odaklı, tekrar oranı yüksek",
        "chain": ["etkinlik mekanı", "turizm", "catering", "yemek blogları"],
        "tone": "Lezzetli, samimi, davetkar",
        "keywords": ["menü", "rezervasyon", "özel gün", "paket servis"],
        "seasonal": ["ramazan", "yılbaşı", "sevgililer günü"]
    },
    "kafe": {
        "analysis": "atmosfer, wifi, ürün çeşitliliği, süreklilik",
        "chain": ["kitapçı", "çalışma alanı", "pastane", "workshop"],
        "tone": "Rahat, sıcak, modern",
        "keywords": ["kahve", "atıştırmalık", "wifi", "toplantı"],
        "seasonal": ["kış", "yaz", "öğrenci dönemi"]
    },
    "spor salonu": {
        "analysis": "ekipman, eğitmen, esneklik, sonuç odaklı",
        "chain": ["beslenme uzmanı", "fizyoterapist", "spor mağazası"],
        "tone": "Motivasyonel, sağlıklı, disiplinli",
        "keywords": ["üyelik", "personal trainer", "grup dersi", "fitness"],
        "seasonal": ["yaza hazırlık", "yeni yıl kararları"]
    },
    "default": {
        "analysis": "genel, fiyat ve kalite odaklı, müşteri ilişkileri",
        "chain": ["benzer hizmetler", "tamamlayıcı sektörler"],
        "tone": "Profesyonel, güvenilir, çözüm odaklı",
        "keywords": ["kalite", "hizmet", "müşteri memnuniyeti"],
        "seasonal": []
    }
}

class ConfigManager:
    """Ayarlar yöneticisi"""

    def __init__(self):
        self.config_file = Path.home() / '.local_business_strategy' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        """Ayarları yükle"""
        default_settings = {
            'ai_model': 'deepseek',
            'max_length': 800,
            'language': 'TR',
            'theme': 'light',
            'auto_save': True,
            'api_key': '',
            'last_used_templates': [],
            'export_path': str(Path.home() / 'Desktop')
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except Exception as e:
                print(f"Ayarlar yüklenemedi: {e}")

        return default_settings

    def save_settings(self):
        """Ayarları kaydet"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ayarlar kaydedilemedi: {e}")
            return False

    def get(self, key, default=None):
        """Ayar değerini al"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Ayar değerini güncelle"""
        self.settings[key] = value
        self.save_settings()

class AIIntegration:
    """AI entegrasyon modülü"""

    def __init__(self, config_manager):
        self.config = config_manager
        self.local_model = None
        self.tokenizer = None
        self.setup_local_model()

    def setup_local_model(self):
        """Yerel modeli kur"""
        if TORCH_AVAILABLE and self.config.get('ai_model') != 'deepseek':
            try:
                model_name = self.config.get('ai_model', 'gpt2')
                self.local_model = pipeline('text-generation', model=model_name)
                print(f"Yerel model yüklendi: {model_name}")
            except Exception as e:
                print(f"Yerel model yüklenemedi: {e}")
                self.local_model = None

    def generate_with_deepseek(self, prompt, max_tokens=800):
        """DeepSeek API ile üret"""
        if not REQUESTS_AVAILABLE:
            return None, "Requests modülü yüklü değil"

        api_key = self.config.get('api_key', '').strip()
        if not api_key:
            # Demo key - gerçek kullanımda kaldırılmalı
            api_key = "sk-fedc2373fb6f4751bccd7019c571f3f8"

        endpoint = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Sen bir iş stratejisti ve pazarlama uzmanısın. Gerçekçi, uygulanabilir stratejiler üret."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'], None
        except requests.exceptions.RequestException as e:
            return None, f"API hatası: {e}"
        except Exception as e:
            return None, f"İşlem hatası: {e}"

    def generate_local(self, prompt, max_length=800):
        """Yerel model ile üret"""
        if not self.local_model:
            return None, "Yerel model yüklenemedi"

        try:
            result = self.local_model(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                truncation=True
            )
            return result[0]['generated_text'], None
        except Exception as e:
            return None, f"Yerel üretim hatası: {e}"

    def generate_fallback(self, business_data):
        """Offline fallback strateji"""
        industry = business_data.get('sector', '').lower()
        industry_info = INDUSTRY_DATABASE.get(industry, INDUSTRY_DATABASE['default'])

        template = f"""
📊 İŞLETME STRATEJİ RAPORU
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}
İşletme: {business_data.get('sector', 'Bilinmiyor')}

1️⃣ DURUM ANALİZİ
• Sektör: {business_data.get('sector')}
• Alt Sektör: {business_data.get('sub_sector', 'Genel')}
• Bölge: {business_data.get('region', 'Belirtilmedi')}
• Çalışma Modeli: {business_data.get('model', 'Yerel')}
• Öncelik: {business_data.get('priority', 'Marka Bilinirliği')}

2️⃣ GÜÇLÜ YÖNLER
• Yerel bilgi ve ağ
• Kişiselleştirilmiş hizmet
• Hızlı karar verme
• Düşük operasyon maliyeti

3️⃣ ZAYIF YÖNLER
• Sınırlı kaynak
• Marka bilinirliği eksikliği
• Dijital varlık sınırlı

4️⃣ FIRSATLAR
• Yerel iş birlikleri ({', '.join(industry_info['chain'])})
• Sosyal medya pazarlaması
• Yerel SEO optimizasyonu
• Müşteri sadakat programları

5️⃣ TEHDİTLER
• Büyük zincirler
• Ekonomik dalgalanmalar
• Dijital dönüşüm gereksinimi

🎯 AKSİYON PLANI

BİRİNCİ HAFTA (Acil Eylemler):
1. Google İşletme Profili'ni oluştur/güncelle
2. Temel sosyal medya hesaplarını aç
3. 5 potansiyel müşteri ile iletişime geç
4. Rakip analizi yap
5. Basit bir promosyon planla

İLK AY (Temel Kurulum):
1. Web sitesi/landing page hazırla
2. Müşteri yönetim sistemi kur
3. Yerel iş birlikleri ara
4. İçerik takvimi oluştur
5. Temel CRM sistemi

İLK 3 AY (Büyüme):
1. E-posta pazarlama başlat
2. Referans programı oluştur
3. Yerel etkinliklere katıl
4. Online rezervasyon sistemi
5. Sadakat kartı uygulaması

💡 ÖNERİLER
• {industry_info['tone']} tonunda iletişim kur
• {', '.join(industry_info['keywords'])} anahtar kelimelerini kullan
• Yerel influencer'larla çalış
• Müşteri yorumlarını topla ve paylaş

📞 İLETİŞİM STRATEJİSİ
Örnek Mesaj: "Merhaba! [Bölge]'deki {business_data.get('sector')} işletmemizle size nasıl yardımcı olabiliriz? Özel teklifimizden yararlanmak için bugün bizi ziyaret edin!"

⏰ TAKİP
• Haftalık: Satış ve müşteri analizi
• Aylık: Strateji gözden geçirme
• 3 Aylık: Büyüme metrikleri değerlendirme
        """

        return template, None

    def generate_strategy(self, business_data):
        """Ana strateji üretme fonksiyonu"""
        language = self.config.get('language', 'TR')
        max_tokens = self.config.get('max_length', 800)

        # Prompt hazırlama
        prompt = self.create_prompt(business_data, language)

        # AI seçeneğine göre üret
        ai_model = self.config.get('ai_model', 'deepseek')

        if ai_model == 'deepseek' and REQUESTS_AVAILABLE:
            result, error = self.generate_with_deepseek(prompt, max_tokens)
            if not error:
                return result
            print(f"DeepSeek hatası: {error}")

        if TORCH_AVAILABLE and self.local_model:
            result, error = self.generate_local(prompt, max_tokens)
            if not error:
                return result
            print(f"Yerel model hatası: {error}")

        # Fallback strateji
        result, error = self.generate_fallback(business_data)
        if not error:
            return result

        return "Strateji üretilemedi. Lütfen ayarlarınızı kontrol edin."

    def create_prompt(self, business_data, language='TR'):
        """Prompt oluştur"""

        sector = business_data.get('sector', '')
        sub_sector = business_data.get('sub_sector', 'genel')
        products = business_data.get('products', 'standart')
        model = business_data.get('model', 'Yerel')
        region = business_data.get('region', 'bilinmiyor')
        priority = business_data.get('priority', 'Marka Bilinirliği')

        industry_info = INDUSTRY_DATABASE.get(sector.lower(), INDUSTRY_DATABASE['default'])

        if language == 'TR':
            return f"""
Yerel bir {sector} işletmesi için kapsamlı iş stratejisi ve pazarlama planı oluştur.

İŞLETME BİLGİLERİ:
• Ana Sektör: {sector}
• Alt Sektör / Uzmanlık: {sub_sector}
• Ürün/Hizmet: {products}
• Çalışma Modeli: {model}
• Hedef Bölge: {region}
• Öncelikli Hedef: {priority}

SEKTÖR ANALİZİ:
{industry_info['analysis']}
Anahtar Kelimeler: {', '.join(industry_info['keywords'])}
Mevsimsel Fırsatlar: {', '.join(industry_info['seasonal'])}
Zincir İş Birlikleri: {', '.join(industry_info['chain'])}

İÇERİK İSTENEN FORMAT:

1. ÖZET ve SWOT ANALİZİ
   • Mevcut Durum
   • Güçlü Yönler
   • Zayıf Yönler
   • Fırsatlar
   • Tehditler

2. PAZARLAMA STRATEJİSİ
   • Hedef Kitle
   • Benzersiz Satış Teklifi (USP)
   • Fiyatlandırma Stratejisi
   • Dağıtım Kanalları

3. DİJİTAL PAZARLAMA PLANI
   • Web Sitesi Önerileri
   • Sosyal Medya Stratejisi
   • SEO Optimizasyonu
   • E-posta Pazarlaması
   • Online Reklamlar

4. YEREL PAZARLAMA
   • Yerel İş Birlikleri
   • Etkinlik Katılımı
   • Yerel Medya
   • Referans Programı

5. AKSİYON PLANI (Zaman Çizelgesi)
   • İlk 1 Hafta (Acil Eylemler)
   • İlk 1 Ay (Temel Kurulum)
   • İlk 3 Ay (Büyüme)
   • İlk 6 Ay (Konsolidasyon)

6. BÜTÇE ve KAYNAK PLANI
   • Tahmini Maliyetler
   • ROI Beklentileri
   • Öncelikli Yatırımlar

7. ÖLÇÜM ve TAKİP
   • KPI'lar (Ana Performans Göstergeleri)
   • Haftalık/Aylık Raporlama
   • Strateji Gözden Geçirme

8. İLETİŞİM ve MESAJLAŞMA
   • Marka Tonu: {industry_info['tone']}
   • Örnek Mesajlar
   • Müşteri İletişim Protokolleri

Lütfen gerçekçi, uygulanabilir, bütçe dostu ve ölçülebilir stratejiler öner.
{region} bölgesinin özelliklerini dikkate al.
            """
        else:
            # İngilizce prompt
            return f"""
Create a comprehensive business strategy and marketing plan for a local {sector} business.

BUSINESS INFORMATION:
• Main Sector: {sector}
• Sub-Sector / Specialty: {sub_sector}
• Products/Services: {products}
• Business Model: {model}
• Target Region: {region}
• Priority Goal: {priority}

SECTOR ANALYSIS:
{industry_info['analysis']}
Keywords: {', '.join(industry_info['keywords'])}
Seasonal Opportunities: {', '.join(industry_info['seasonal'])}
Chain Partnerships: {', '.join(industry_info['chain'])}

REQUESTED FORMAT:

1. SUMMARY and SWOT ANALYSIS
   • Current Situation
   • Strengths
   • Weaknesses
   • Opportunities
   • Threats

2. MARKETING STRATEGY
   • Target Audience
   • Unique Selling Proposition (USP)
   • Pricing Strategy
   • Distribution Channels

3. DIGITAL MARKETING PLAN
   • Website Recommendations
   • Social Media Strategy
   • SEO Optimization
   • Email Marketing
   • Online Advertising

4. LOCAL MARKETING
   • Local Partnerships
   • Event Participation
   • Local Media
   • Referral Program

5. ACTION PLAN (Timeline)
   • First 1 Week (Urgent Actions)
   • First 1 Month (Basic Setup)
   • First 3 Months (Growth)
   • First 6 Months (Consolidation)

6. BUDGET and RESOURCE PLAN
   • Estimated Costs
   • ROI Expectations
   • Priority Investments

7. MEASUREMENT and TRACKING
   • KPIs (Key Performance Indicators)
   • Weekly/Monthly Reporting
   • Strategy Review

8. COMMUNICATION and MESSAGING
   • Brand Tone: {industry_info['tone']}
   • Sample Messages
   • Customer Communication Protocols

Please suggest realistic, actionable, budget-friendly and measurable strategies.
Consider the specifics of the {region} region.
            """

class TemplateManager:
    """Şablon yöneticisi"""

    def __init__(self):
        self.templates_dir = Path.home() / '.local_business_strategy' / 'templates'
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def save_template(self, name, content):
        """Şablon kaydet"""
        template_file = self.templates_dir / f"{name}.json"
        try:
            template_data = {
                'name': name,
                'content': content,
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat()
            }
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Şablon kaydedilemedi: {e}")
            return False

    def load_template(self, name):
        """Şablon yükle"""
        template_file = self.templates_dir / f"{name}.json"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Şablon yüklenemedi: {e}")
        return None

    def list_templates(self):
        """Şablonları listele"""
        templates = []
        for file in self.templates_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    templates.append(data['name'])
            except:
                continue
        return templates

    def delete_template(self, name):
        """Şablon sil"""
        template_file = self.templates_dir / f"{name}.json"
        if template_file.exists():
            template_file.unlink()
            return True
        return False

class ExportManager:
    """Export yöneticisi"""

    @staticmethod
    def export_txt(content, filepath):
        """TXT olarak export"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def export_pdf(content, filepath):
        """PDF olarak export"""
        if not FPDF_AVAILABLE:
            return False, "FPDF modülü yüklü değil"

        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Başlık
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="İşletme Strateji Raporu", ln=True, align='C')
            pdf.ln(10)

            # Tarih
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
            pdf.ln(10)

            # İçerik
            pdf.set_font("Arial", size=12)
            for line in content.split('\n'):
                if line.strip().startswith('•') or line.strip().startswith('-'):
                    pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 6, txt=line)
                elif ':' in line and len(line) < 100:
                    pdf.set_font("Arial", 'B', 12)
                    pdf.multi_cell(0, 8, txt=line)
                else:
                    pdf.set_font("Arial", size=12)
                    pdf.multi_cell(0, 6, txt=line)
                pdf.ln(2)

            pdf.output(filepath)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def export_json(data, filepath):
        """JSON olarak export"""
        try:
            export_data = {
                'meta': {
                    'created': datetime.now().isoformat(),
                    'version': CONFIG['version'],
                    'type': 'business_strategy'
                },
                'content': data
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def export_html(content, filepath):
        """HTML olarak export"""
        try:
            html_template = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>İşletme Strateji Raporu</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        .content {{ max-width: 800px; margin: 0 auto; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ color: #2c3e50; border-left: 4px solid #3498db; padding-left: 10px; margin-bottom: 15px; }}
        .item {{ margin-bottom: 10px; }}
        .timestamp {{ color: #7f8c8d; font-size: 0.9em; text-align: right; margin-top: 40px; }}
        @media print {{
            body {{ margin: 20px; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>İşletme Strateji Raporu</h1>
        <p>Yerel İşletme Strateji Motoru v{CONFIG['version']}</p>
    </div>
    <div class="content">
        <div class="timestamp">
            Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        </div>
        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{content}</pre>
    </div>
    <div class="timestamp">
        <button class="no-print" onclick="window.print()">Yazdır</button>
    </div>
</body>
</html>
            """
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_template)
            return True, None
        except Exception as e:
            return False, str(e)

class StrategyApp:
    """Ana uygulama sınıfı"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"Yerel İşletme Strateji Motoru v{CONFIG['version']}")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Temel değişkenler
        self.config_manager = ConfigManager()
        self.ai_integration = AIIntegration(self.config_manager)
        self.template_manager = TemplateManager()
        self.export_manager = ExportManager()

        # İşletme verileri
        self.business_data = {}

        # GUI değişkenleri
        self.current_theme = self.config_manager.get('theme', 'light')

        # Setup
        self.setup_ui()
        self.apply_theme()
        self.check_dependencies()

        # Auto-save timer
        if self.config_manager.get('auto_save', True):
            self.setup_auto_save()

    def setup_ui(self):
        """UI kurulumu"""
        # Ana container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Sekme 1: Ana Form
        self.form_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.form_frame, text="İşletme Bilgileri")
        self.create_form_tab()

        # Sekme 2: Strateji Görüntüleme
        self.strategy_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.strategy_frame, text="Strateji Raporu")
        self.create_strategy_tab()

        # Sekme 3: Şablonlar
        self.templates_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.templates_frame, text="Şablonlar")
        self.create_templates_tab()

        # Sekme 4: Geçmiş
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="Geçmiş")
        self.create_history_tab()

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Hazır", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Menü bar
        self.create_menu()

    def create_form_tab(self):
        """Form sekmesi oluştur"""
        # Scrollable frame
        canvas = tk.Canvas(self.form_frame)
        scrollbar = ttk.Scrollbar(self.form_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Form elemanları
        row = 0

        # Sektör
        ttk.Label(self.scrollable_frame, text="Sektör*:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.sector_var = tk.StringVar()
        self.sector_combo = ttk.Combobox(
            self.scrollable_frame,
            textvariable=self.sector_var,
            values=list(INDUSTRY_DATABASE.keys())[:-1],  # 'default' hariç
            width=40,
            state='normal'
        )
        self.sector_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        self.sector_combo.bind('<KeyRelease>', self.filter_sectors)
        row += 1

        # Alt Sektör
        ttk.Label(self.scrollable_frame, text="Alt Sektör / Uzmanlık:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.sub_sector_var = tk.StringVar()
        self.sub_sector_entry = ttk.Entry(self.scrollable_frame, textvariable=self.sub_sector_var, width=40)
        self.sub_sector_entry.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Ürün/Hizmet
        ttk.Label(self.scrollable_frame, text="Ürün/Hizmet:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.products_var = tk.StringVar()
        self.products_entry = ttk.Entry(self.scrollable_frame, textvariable=self.products_var, width=40)
        self.products_entry.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Çalışma Modeli
        ttk.Label(self.scrollable_frame, text="Çalışma Modeli:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.model_var = tk.StringVar(value="Yerel")
        model_combo = ttk.Combobox(
            self.scrollable_frame,
            textvariable=self.model_var,
            values=["Yerel", "Online", "Hibrit", "Franchise", "Mobile"],
            state="readonly",
            width=40
        )
        model_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Bölge
        ttk.Label(self.scrollable_frame, text="Hedef Bölge*:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.region_var = tk.StringVar()
        self.region_entry = ttk.Entry(self.scrollable_frame, textvariable=self.region_var, width=40)
        self.region_entry.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Öncelik
        ttk.Label(self.scrollable_frame, text="Öncelikli Hedef:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.priority_var = tk.StringVar(value="Marka Bilinirliği")
        priority_combo = ttk.Combobox(
            self.scrollable_frame,
            textvariable=self.priority_var,
            values=["Hızlı Satış", "Marka Bilinirliği", "Sadık Müşteri", "Pazar Payı", "Kârlılık"],
            state="readonly",
            width=40
        )
        priority_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Bütçe
        ttk.Label(self.scrollable_frame, text="Aylık Pazarlama Bütçesi (₺):").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.budget_var = tk.StringVar(value="1000-5000")
        budget_combo = ttk.Combobox(
            self.scrollable_frame,
            textvariable=self.budget_var,
            values=["0-1000", "1000-5000", "5000-10000", "10000-20000", "20000+"],
            state="readonly",
            width=40
        )
        budget_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Personel
        ttk.Label(self.scrollable_frame, text="Çalışan Sayısı:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        self.staff_var = tk.StringVar(value="1-3")
        staff_combo = ttk.Combobox(
            self.scrollable_frame,
            textvariable=self.staff_var,
            values=["1-3", "4-10", "11-20", "20+"],
            state="readonly",
            width=40
        )
        staff_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        # Mevcut Dijital Varlık
        ttk.Label(self.scrollable_frame, text="Mevcut Dijital Varlık:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, padx=10, pady=5, sticky='w', columnspan=2)
        row += 1

        self.var_website = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="Web Sitesi", variable=self.var_website).grid(
            row=row, column=0, padx=20, pady=2, sticky='w')

        self.var_social = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="Sosyal Medya", variable=self.var_social).grid(
            row=row, column=1, padx=20, pady=2, sticky='w')
        row += 1

        self.var_google = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="Google İşletme Profili", variable=self.var_google).grid(
            row=row, column=0, padx=20, pady=2, sticky='w')

        self.var_pos = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="POS/Ödeme Sistemi", variable=self.var_pos).grid(
            row=row, column=1, padx=20, pady=2, sticky='w')
        row += 1

        self.var_email = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="E-posta Listesi", variable=self.var_email).grid(
            row=row, column=0, padx=20, pady=2, sticky='w')

        self.var_crm = tk.BooleanVar()
        ttk.Checkbutton(self.scrollable_frame, text="CRM Sistemi", variable=self.var_crm).grid(
            row=row, column=1, padx=20, pady=2, sticky='w')
        row += 1

        # Ek Notlar
        ttk.Label(self.scrollable_frame, text="Ek Notlar / Özel İstekler:").grid(
            row=row, column=0, padx=10, pady=5, sticky='w')
        row += 1

        self.notes_text = scrolledtext.ScrolledText(self.scrollable_frame, width=50, height=5)
        self.notes_text.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
        row += 1

        # Butonlar
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="📊 Strateji Üret",
                  command=self.generate_strategy_threaded,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="💾 Şablon Olarak Kaydet",
                  command=self.save_as_template,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="🗑️ Formu Temizle",
                  command=self.clear_form,
                  width=20).pack(side=tk.LEFT, padx=5)

        # Grid weight ayarları
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

    def create_strategy_tab(self):
        """Strateji görüntüleme sekmesi"""
        # Toolbar
        toolbar = ttk.Frame(self.strategy_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="📋 Kopyala", command=self.copy_strategy).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📄 TXT Kaydet", command=lambda: self.export_strategy('txt')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📊 PDF Kaydet", command=lambda: self.export_strategy('pdf')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🌐 HTML Kaydet", command=lambda: self.export_strategy('html')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🖨️ Yazdır", command=self.print_strategy).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 Yenile", command=self.refresh_strategy).pack(side=tk.LEFT, padx=2)

        # Strateji görüntüleme alanı
        self.strategy_text = scrolledtext.ScrolledText(
            self.strategy_frame,
            wrap=tk.WORD,
            font=('Consolas', 10)
        )
        self.strategy_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Başlangıç mesajı
        welcome_msg = """YEREL İŞLETME STRATEJİ MOTORU v2.0.0
========================================

Hoş geldiniz!

1. 'İşletme Bilgileri' sekmesinden işletme bilgilerinizi doldurun.
2. 'Strateji Üret' butonuna tıklayın.
3. Oluşturulan stratejiyi bu sekmede görüntüleyin.
4. İstediğiniz formatta kaydedin veya yazdırın.

📍 Önemli: Sektör ve Bölge alanları zorunludur.

🔧 Desteklenen AI Modelleri:
   • DeepSeek API (Tavsiye edilen)
   • Yerel Transformers modelleri
   • Offline fallback stratejileri

💡 İpucu: Ayarlar menüsünden AI modelinizi ve dilinizi değiştirebilirsiniz.
        """
        self.strategy_text.insert(tk.END, welcome_msg)
        self.strategy_text.config(state=tk.DISABLED)

    def create_templates_tab(self):
        """Şablonlar sekmesi"""
        # Şablon listesi
        list_frame = ttk.Frame(self.templates_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(list_frame, text="Kayıtlı Şablonlar:", font=('Arial', 10, 'bold')).pack(anchor='w')

        self.template_listbox = tk.Listbox(list_frame, height=15)
        self.template_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        # Şablon yönetimi butonları
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Yükle", command=self.load_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Sil", command=self.delete_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Listeyi Yenile", command=self.refresh_templates).pack(side=tk.LEFT, padx=2)

        # Şablon önizleme
        preview_frame = ttk.Frame(self.templates_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(preview_frame, text="Şablon Önizleme:", font=('Arial', 10, 'bold')).pack(anchor='w')

        self.template_preview = scrolledtext.ScrolledText(preview_frame, height=20)
        self.template_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        # Başlangıçta listeyi doldur
        self.refresh_templates()

    def create_history_tab(self):
        """Geçmiş sekmesi"""
        # Geçmiş listesi
        history_frame = ttk.Frame(self.history_frame)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(history_frame, text="Son Stratejiler:", font=('Arial', 10, 'bold')).pack(anchor='w')

        self.history_listbox = tk.Listbox(history_frame, height=20)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        # Geçmiş yönetimi
        button_frame = ttk.Frame(history_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Yeniden Yükle", command=self.load_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Temizle", command=self.clear_history).pack(side=tk.LEFT, padx=2)

    def create_menu(self):
        """Menü bar oluştur"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Dosya menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Yeni Strateji", command=self.clear_form)
        file_menu.add_command(label="Aç...", command=self.load_strategy_file)
        file_menu.add_separator()
        file_menu.add_command(label="TXT Olarak Kaydet", command=lambda: self.export_strategy('txt'))
        file_menu.add_command(label="PDF Olarak Kaydet", command=lambda: self.export_strategy('pdf'))
        file_menu.add_separator()
        file_menu.add_command(label="Ayarlar", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.root.quit)

        # Düzen menüsü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Düzen", menu=edit_menu)
        edit_menu.add_command(label="Kopyala", command=self.copy_strategy)
        edit_menu.add_command(label="Tümünü Seç", command=self.select_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="Temala", command=self.toggle_theme)

        # Araçlar menüsü
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Araçlar", menu=tools_menu)
        tools_menu.add_command(label="Bağımlılıkları Kontrol Et", command=self.check_dependencies)
        tools_menu.add_command(label="Sistem Bilgisi", command=self.show_system_info)
        tools_menu.add_separator()
        tools_menu.add_command(label="API Anahtarını Yapılandır", command=self.configure_api_key)

        # Yardım menüsü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        help_menu.add_command(label="Kullanım Kılavuzu", command=self.show_help)
        help_menu.add_command(label="Hata Bildir", command=self.report_bug)
        help_menu.add_separator()
        help_menu.add_command(label="Hakkında", command=self.show_about)

    def filter_sectors(self, event=None):
        """Sektör filtreleme"""
        current = self.sector_var.get().lower()
        if current:
            filtered = [s for s in INDUSTRY_DATABASE.keys() if s.lower().startswith(current) and s != 'default']
            self.sector_combo['values'] = filtered
            if filtered:
                self.sector_combo.event_generate('<Down>')
        else:
            self.sector_combo['values'] = list(INDUSTRY_DATABASE.keys())[:-1]

    def generate_strategy_threaded(self):
        """Strateji üretimi (threaded)"""
        # Form doğrulama
        if not self.sector_var.get().strip():
            messagebox.showerror("Hata", "Lütfen bir sektör seçin!")
            return

        if not self.region_var.get().strip():
            messagebox.showerror("Hata", "Lütfen hedef bölgeyi girin!")
            return

        # İşletme verilerini topla
        self.business_data = {
            'sector': self.sector_var.get(),
            'sub_sector': self.sub_sector_var.get(),
            'products': self.products_var.get(),
            'model': self.model_var.get(),
            'region': self.region_var.get(),
            'priority': self.priority_var.get(),
            'budget': self.budget_var.get(),
            'staff': self.staff_var.get(),
            'website': self.var_website.get(),
            'social': self.var_social.get(),
            'google': self.var_google.get(),
            'pos': self.var_pos.get(),
            'email': self.var_email.get(),
            'crm': self.var_crm.get(),
            'notes': self.notes_text.get("1.0", tk.END).strip()
        }

        # Progress göstergesi
        self.show_progress("Strateji üretiliyor...")

        # Thread başlat
        thread = threading.Thread(target=self.generate_strategy_worker)
        thread.daemon = True
        thread.start()

    def generate_strategy_worker(self):
        """Strateji üretim işçisi"""
        try:
            # AI ile strateji üret
            strategy = self.ai_integration.generate_strategy(self.business_data)

            # GUI güncellemesi
            self.root.after(0, self.update_strategy_display, strategy)

            # Geçmişe ekle
            self.add_to_history(strategy)

            # Başarı mesajı
            self.root.after(0, self.hide_progress)
            self.root.after(0, lambda: self.update_status("Strateji başarıyla oluşturuldu"))

        except Exception as e:
            self.root.after(0, self.hide_progress)
            self.root.after(0, lambda: messagebox.showerror("Hata", f"Strateji üretilemedi: {str(e)}"))

    def update_strategy_display(self, strategy):
        """Strateji görüntüleme alanını güncelle"""
        self.strategy_text.config(state=tk.NORMAL)
        self.strategy_text.delete(1.0, tk.END)
        self.strategy_text.insert(tk.END, strategy)
        self.strategy_text.config(state=tk.NORMAL)

        # Strateji sekmesine geç
        self.notebook.select(1)

    def show_progress(self, message="İşleniyor..."):
        """Progress göstergesi göster"""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Lütfen Bekleyin")
        self.progress_window.geometry("300x100")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()

        # Progress bar
        ttk.Label(self.progress_window, text=message).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_window, mode='indeterminate')
        self.progress_bar.pack(pady=10, padx=20, fill=tk.X)
        self.progress_bar.start(10)

        # Pencereyi merkezle
        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (self.progress_window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (self.progress_window.winfo_height() // 2)
        self.progress_window.geometry(f"+{x}+{y}")

    def hide_progress(self):
        """Progress göstergesini gizle"""
        if hasattr(self, 'progress_window'):
            self.progress_bar.stop()
            self.progress_window.destroy()

    def update_status(self, message):
        """Status bar'ı güncelle"""
        self.status_bar.config(text=f" {message}")

    def copy_strategy(self):
        """Stratejiyi kopyala"""
        try:
            strategy = self.strategy_text.get(1.0, tk.END).strip()
            if strategy:
                self.root.clipboard_clear()
                self.root.clipboard_append(strategy)
                self.update_status("Strateji panoya kopyalandı")
                messagebox.showinfo("Başarılı", "Strateji panoya kopyalandı!")
            else:
                messagebox.showwarning("Uyarı", "Kopyalanacak strateji bulunamadı!")
        except Exception as e:
            messagebox.showerror("Hata", f"Kopyalama başarısız: {str(e)}")

    def export_strategy(self, format_type):
        """Stratejiyi export et"""
        strategy = self.strategy_text.get(1.0, tk.END).strip()
        if not strategy:
            messagebox.showwarning("Uyarı", "Export edilecek strateji bulunamadı!")
            return

        # Varsayılan dosya adı
        default_name = f"strateji_{datetime.now().strftime('%Y%m%d_%H%M')}"

        if format_type == 'txt':
            filetypes = [("Text files", "*.txt"), ("All files", "*.*")]
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=filetypes,
                initialfile=f"{default_name}.txt"
            )
            if filename:
                success, error = self.export_manager.export_txt(strategy, filename)

        elif format_type == 'pdf':
            filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=filetypes,
                initialfile=f"{default_name}.pdf"
            )
            if filename:
                success, error = self.export_manager.export_pdf(strategy, filename)

        elif format_type == 'html':
            filetypes = [("HTML files", "*.html"), ("All files", "*.*")]
            filename = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=filetypes,
                initialfile=f"{default_name}.html"
            )
            if filename:
                success, error = self.export_manager.export_html(strategy, filename)

        else:
            messagebox.showerror("Hata", "Desteklenmeyen format!")
            return

        if filename and 'success' in locals():
            if success:
                messagebox.showinfo("Başarılı", f"Strateji {format_type.upper()} olarak kaydedildi!")
                self.update_status(f"Dosya kaydedildi: {os.path.basename(filename)}")
            else:
                messagebox.showerror("Hata", f"Kayıt başarısız: {error}")

    def save_as_template(self):
        """Şablon olarak kaydet"""
        if not self.sector_var.get().strip():
            messagebox.showerror("Hata", "Önce sektör bilgisini girin!")
            return

        template_name = tk.simpledialog.askstring(
            "Şablon Kaydet",
            "Şablon adını girin:",
            initialvalue=f"{self.sector_var.get()}_{self.region_var.get()}"
        )

        if template_name:
            template_data = {
                'sector': self.sector_var.get(),
                'sub_sector': self.sub_sector_var.get(),
                'products': self.products_var.get(),
                'model': self.model_var.get(),
                'region': self.region_var.get(),
                'priority': self.priority_var.get(),
                'budget': self.budget_var.get(),
                'staff': self.staff_var.get(),
                'website': self.var_website.get(),
                'social': self.var_social.get(),
                'google': self.var_google.get(),
                'pos': self.var_pos.get(),
                'email': self.var_email.get(),
                'crm': self.var_crm.get(),
                'notes': self.notes_text.get("1.0", tk.END).strip()
            }

            if self.template_manager.save_template(template_name, template_data):
                messagebox.showinfo("Başarılı", "Şablon kaydedildi!")
                self.refresh_templates()
            else:
                messagebox.showerror("Hata", "Şablon kaydedilemedi!")

    def load_template(self):
        """Şablon yükle"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir şablon seçin!")
            return

        template_name = self.template_listbox.get(selection[0])
        template = self.template_manager.load_template(template_name)

        if template:
            data = template.get('content', {})

            # Form alanlarını doldur
            self.sector_var.set(data.get('sector', ''))
            self.sub_sector_var.set(data.get('sub_sector', ''))
            self.products_var.set(data.get('products', ''))
            self.model_var.set(data.get('model', 'Yerel'))
            self.region_var.set(data.get('region', ''))
            self.priority_var.set(data.get('priority', 'Marka Bilinirliği'))
            self.budget_var.set(data.get('budget', '1000-5000'))
            self.staff_var.set(data.get('staff', '1-3'))

            self.var_website.set(data.get('website', False))
            self.var_social.set(data.get('social', False))
            self.var_google.set(data.get('google', False))
            self.var_pos.set(data.get('pos', False))
            self.var_email.set(data.get('email', False))
            self.var_crm.set(data.get('crm', False))

            self.notes_text.delete(1.0, tk.END)
            self.notes_text.insert(1.0, data.get('notes', ''))

            messagebox.showinfo("Başarılı", f"'{template_name}' şablonu yüklendi!")
            self.update_status(f"Şablon yüklendi: {template_name}")
        else:
            messagebox.showerror("Hata", "Şablon yüklenemedi!")

    def delete_template(self):
        """Şablon sil"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir şablon seçin!")
            return

        template_name = self.template_listbox.get(selection[0])

        if messagebox.askyesno("Onay", f"'{template_name}' şablonunu silmek istediğinize emin misiniz?"):
            if self.template_manager.delete_template(template_name):
                self.refresh_templates()
                messagebox.showinfo("Başarılı", "Şablon silindi!")
            else:
                messagebox.showerror("Hata", "Şablon silinemedi!")

    def refresh_templates(self):
        """Şablon listesini yenile"""
        self.template_listbox.delete(0, tk.END)
        templates = self.template_manager.list_templates()
        for template in templates:
            self.template_listbox.insert(tk.END, template)

        self.template_preview.delete(1.0, tk.END)
        self.template_preview.insert(tk.END, f"Toplam {len(templates)} şablon yüklü.")

    def add_to_history(self, strategy):
        """Geçmişe ekle"""
        history_file = Path.home() / '.local_business_strategy' / 'history.json'
        history_file.parent.mkdir(parents=True, exist_ok=True)

        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'sector': self.business_data.get('sector'),
            'region': self.business_data.get('region'),
            'strategy_preview': strategy[:200] + "..." if len(strategy) > 200 else strategy,
            'full_strategy': strategy
        }

        history_data = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
            except:
                history_data = []

        # En fazla 50 kayıt
        history_data.insert(0, history_entry)
        history_data = history_data[:CONFIG['max_history']]

        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
        except:
            pass

        # Geçmiş listesini güncelle
        self.load_history()

    def load_history(self):
        """Geçmişi yükle"""
        history_file = Path.home() / '.local_business_strategy' / 'history.json'
        self.history_listbox.delete(0, tk.END)

        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)

                for entry in history_data:
                    timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%d.%m.%Y %H:%M')
                    display = f"{timestamp} - {entry['sector']} ({entry['region']})"
                    self.history_listbox.insert(tk.END, display)

            except Exception as e:
                self.history_listbox.insert(tk.END, f"Geçmiş yüklenemedi: {str(e)}")

    def clear_history(self):
        """Geçmişi temizle"""
        if messagebox.askyesno("Onay", "Tüm geçmişi silmek istediğinize emin misiniz?"):
            history_file = Path.home() / '.local_business_strategy' / 'history.json'
            if history_file.exists():
                history_file.unlink()
            self.history_listbox.delete(0, tk.END)
            messagebox.showinfo("Başarılı", "Geçmiş temizlendi!")

    def clear_form(self):
        """Formu temizle"""
        if messagebox.askyesno("Onay", "Formu temizlemek istediğinize emin misiniz?"):
            self.sector_var.set('')
            self.sub_sector_var.set('')
            self.products_var.set('')
            self.model_var.set('Yerel')
            self.region_var.set('')
            self.priority_var.set('Marka Bilinirliği')
            self.budget_var.set('1000-5000')
            self.staff_var.set('1-3')

            self.var_website.set(False)
            self.var_social.set(False)
            self.var_google.set(False)
            self.var_pos.set(False)
            self.var_email.set(False)
            self.var_crm.set(False)

            self.notes_text.delete(1.0, tk.END)

            self.update_status("Form temizlendi")

    def open_settings(self):
        """Ayarlar penceresi"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Ayarlar")
        settings_win.geometry("400x400")
        settings_win.transient(self.root)
        settings_win.grab_set()

        # Notebook
        settings_notebook = ttk.Notebook(settings_win)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Genel ayarlar
        general_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(general_frame, text="Genel")

        row = 0
        ttk.Label(general_frame, text="Dil:").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        lang_combo = ttk.Combobox(general_frame, values=CONFIG['supported_languages'])
        lang_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        lang_combo.set(self.config_manager.get('language', 'TR'))
        row += 1

        ttk.Label(general_frame, text="Tema:").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        theme_combo = ttk.Combobox(general_frame, values=['light', 'dark', 'classic'])
        theme_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        theme_combo.set(self.config_manager.get('theme', 'light'))
        row += 1

        self.auto_save_var = tk.BooleanVar(value=self.config_manager.get('auto_save', True))
        ttk.Checkbutton(general_frame, text="Otomatik kaydet", variable=self.auto_save_var).grid(
            row=row, column=0, columnspan=2, padx=10, pady=5, sticky='w')
        row += 1

        # AI Ayarları
        ai_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(ai_frame, text="AI")

        row = 0
        ttk.Label(ai_frame, text="AI Modeli:").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        ai_model_combo = ttk.Combobox(ai_frame, values=['deepseek', 'gpt2', 'distilgpt2', 'gpt2-medium'])
        ai_model_combo.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        ai_model_combo.set(self.config_manager.get('ai_model', 'deepseek'))
        row += 1

        ttk.Label(ai_frame, text="Max Token:").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        max_token_spin = ttk.Spinbox(ai_frame, from_=100, to=4000, width=10)
        max_token_spin.grid(row=row, column=1, padx=10, pady=5, sticky='w')
        max_token_spin.set(self.config_manager.get('max_length', 800))
        row += 1

        ttk.Label(ai_frame, text="API Anahtarı:").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        self.api_key_var = tk.StringVar(value=self.config_manager.get('api_key', ''))
        api_key_entry = ttk.Entry(ai_frame, textvariable=self.api_key_var, show="*", width=30)
        api_key_entry.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        row += 1

        ttk.Button(ai_frame, text="Anahtarı Test Et", command=self.test_api_key).grid(
            row=row, column=0, columnspan=2, pady=10)

        # Kaydet butonu
        ttk.Button(settings_win, text="Kaydet",
                  command=lambda: self.save_settings(
                      lang_combo.get(),
                      theme_combo.get(),
                      self.auto_save_var.get(),
                      ai_model_combo.get(),
                      int(max_token_spin.get()),
                      self.api_key_var.get(),
                      settings_win
                  )).pack(pady=10)

    def save_settings(self, language, theme, auto_save, ai_model, max_length, api_key, window):
        """Ayarları kaydet"""
        self.config_manager.set('language', language)
        self.config_manager.set('theme', theme)
        self.config_manager.set('auto_save', auto_save)
        self.config_manager.set('ai_model', ai_model)
        self.config_manager.set('max_length', max_length)
        self.config_manager.set('api_key', api_key)

        # AI modelini yeniden yükle
        self.ai_integration.setup_local_model()

        # Temayı uygula
        self.current_theme = theme
        self.apply_theme()

        # Auto-save timer'ı ayarla
        if auto_save:
            self.setup_auto_save()

        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")
        window.destroy()

    def test_api_key(self):
        """API anahtarını test et"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Uyarı", "Lütfen API anahtarını girin!")
            return

        # Test için basit bir prompt
        test_prompt = "Merhaba, bu bir test mesajıdır. Cevap veriyor musun?"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 50
        }

        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                messagebox.showinfo("Başarılı", "API anahtarı geçerli!")
            else:
                messagebox.showerror("Hata", f"API hatası: {response.status_code}")

        except Exception as e:
            messagebox.showerror("Hata", f"Bağlantı hatası: {str(e)}")

    def apply_theme(self):
        """Temayı uygula"""
        theme = self.current_theme

        if theme == 'dark':
            bg_color = '#2b2b2b'
            fg_color = '#ffffff'
            entry_bg = '#3c3c3c'
            entry_fg = '#ffffff'
            button_bg = '#4c4c4c'
        elif theme == 'classic':
            bg_color = '#f0f0f0'
            fg_color = '#000000'
            entry_bg = '#ffffff'
            entry_fg = '#000000'
            button_bg = '#e0e0e0'
        else:  # light
            bg_color = '#ffffff'
            fg_color = '#000000'
            entry_bg = '#ffffff'
            entry_fg = '#000000'
            button_bg = '#f0f0f0'

        # Renkleri uygula
        style = ttk.Style()
        style.theme_use('clam')  # Daha fazla özelleştirme için

        # Widget renkleri
        widgets = [
            self.root, self.main_frame, self.form_frame, self.strategy_frame,
            self.templates_frame, self.history_frame, self.strategy_text,
            self.template_preview, self.notes_text
        ]

        for widget in widgets:
            try:
                widget.config(bg=bg_color, fg=fg_color)
            except:
                pass

        # Entry ve Text widget'ları
        entry_widgets = [
            self.sub_sector_entry, self.products_entry, self.region_entry,
            self.strategy_text, self.template_preview, self.notes_text
        ]

        for widget in entry_widgets:
            try:
                widget.config(bg=entry_bg, fg=entry_fg, insertbackground=fg_color)
            except:
                pass

        # Listbox'lar
        listboxes = [self.template_listbox, self.history_listbox]
        for listbox in listboxes:
            try:
                listbox.config(bg=entry_bg, fg=entry_fg, selectbackground=button_bg)
            except:
                pass

        # Combobox'lar
        comboboxes = [self.sector_combo]
        for combo in comboboxes:
            try:
                combo.config(background=entry_bg, foreground=entry_fg)
            except:
                pass

    def toggle_theme(self):
        """Tema değiştir"""
        themes = ['light', 'dark', 'classic']
        current_index = themes.index(self.current_theme)
        next_index = (current_index + 1) % len(themes)
        self.current_theme = themes[next_index]
        self.config_manager.set('theme', self.current_theme)
        self.apply_theme()
        self.update_status(f"Tema değiştirildi: {self.current_theme}")

    def check_dependencies(self):
        """Bağımlılıkları kontrol et"""
        missing = []

        if not REQUESTS_AVAILABLE:
            missing.append("requests (pip install requests)")

        if self.config_manager.get('ai_model') != 'deepseek' and not TORCH_AVAILABLE:
            missing.append("torch ve transformers (pip install torch transformers)")

        if not FPDF_AVAILABLE:
            missing.append("fpdf (pip install fpdf)")

        if missing:
            message = "Eksik bağımlılıklar:\n\n" + "\n".join(missing)
            message += "\n\nBu modüller yüklenmeli mi?"

            if messagebox.askyesno("Eksik Bağımlılıklar", message):
                self.install_dependencies(missing)
        else:
            messagebox.showinfo("Bağımlılıklar", "Tüm bağımlılıklar yüklü!")

    def install_dependencies(self, missing):
        """Bağımlılıkları yükle (bilgi amaçlı)"""
        install_commands = []

        for dep in missing:
            if "requests" in dep:
                install_commands.append("pip install requests")
            elif "torch" in dep:
                install_commands.append("pip install torch transformers")
            elif "fpdf" in dep:
                install_commands.append("pip install fpdf")

        command_text = "\n".join(install_commands)
        message = f"Terminal/komut isteminde şu komutları çalıştırın:\n\n{command_text}"

        messagebox.showinfo("Yükleme Komutları", message)

    def show_system_info(self):
        """Sistem bilgisi göster"""
        info = f"""
SİSTEM BİLGİSİ

Uygulama: Yerel İşletme Strateji Motoru
Versiyon: {CONFIG['version']}

Python: {sys.version}
Platform: {sys.platform}

BAĞIMLILIKLAR:
• Requests: {'✓ Yüklü' if REQUESTS_AVAILABLE else '✗ Eksik'}
• PyTorch: {'✓ Yüklü' if TORCH_AVAILABLE else '✗ Eksik'}
• FPDF: {'✓ Yüklü' if FPDF_AVAILABLE else '✗ Eksik'}

AYARLAR:
• AI Model: {self.config_manager.get('ai_model', 'deepseek')}
• Dil: {self.config_manager.get('language', 'TR')}
• Max Token: {self.config_manager.get('max_length', 800)}
• Tema: {self.config_manager.get('theme', 'light')}
"""
        messagebox.showinfo("Sistem Bilgisi", info)

    def configure_api_key(self):
        """API anahtarını yapılandır"""
        api_key = tk.simpledialog.askstring(
            "API Anahtarı",
            "DeepSeek API anahtarınızı girin:",
            show='*',
            initialvalue=self.config_manager.get('api_key', '')
        )

        if api_key is not None:
            self.config_manager.set('api_key', api_key)
            messagebox.showinfo("Başarılı", "API anahtarı kaydedildi!")

    def load_strategy_file(self):
        """Strateji dosyası yükle"""
        filetypes = [
            ("Text files", "*.txt"),
            ("JSON files", "*.json"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        strategy = data.get('content', '')
                else:
                    with open(filename, 'r', encoding='utf-8') as f:
                        strategy = f.read()

                self.update_strategy_display(strategy)
                messagebox.showinfo("Başarılı", "Strateji yüklendi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya yüklenemedi: {str(e)}")

    def print_strategy(self):
        """Stratejiyi yazdır (simüle)"""
        strategy = self.strategy_text.get(1.0, tk.END).strip()
        if not strategy:
            messagebox.showwarning("Uyarı", "Yazdırılacak strateji bulunamadı!")
            return

        # Basit bir print dialog simülasyonu
        print_dialog = tk.Toplevel(self.root)
        print_dialog.title("Yazdır")
        print_dialog.geometry("300x200")

        ttk.Label(print_dialog, text="Yazdırma Önizleme", font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(print_dialog, text="Bu bir simülasyondur.").pack(pady=5)
        ttk.Label(print_dialog, text=f"Yazdırılacak karakter: {len(strategy)}").pack(pady=5)

        ttk.Button(print_dialog, text="Tamam", command=print_dialog.destroy).pack(pady=20)

        self.update_status("Yazdırma hazır")

    def refresh_strategy(self):
        """Stratejiyi yenile"""
        if self.business_data:
            self.generate_strategy_threaded()
        else:
            messagebox.showwarning("Uyarı", "Önce bir strateji üretmelisiniz!")

    def select_all(self):
        """Tümünü seç"""
        if self.notebook.index(self.notebook.select()) == 1:  # Strateji sekmesi
            self.strategy_text.tag_add(tk.SEL, "1.0", tk.END)
            self.strategy_text.mark_set(tk.INSERT, "1.0")
            self.strategy_text.see(tk.INSERT)

    def show_help(self):
        """Yardım göster"""
        help_text = """
📚 KULLANIM KILAVUZU

1. İŞLETME BİLGİLERİ SEKMESİ:
   • Zorunlu alanlar: Sektör ve Bölge
   • Sektör seçerken otomatik tamamlama aktif
   • Tüm alanları doldurmanız önerilir

2. STRATEJİ ÜRETME:
   • 'Strateji Üret' butonuna tıklayın
   • AI modelinize göre strateji oluşturulur
   • İnternet bağlantısı gerektirebilir

3. STRATEJİ YÖNETİMİ:
   • Kopyala: Panoya kopyalar
   • Kaydet: TXT, PDF, HTML formatlarında
   • Yazdır: Simüle edilmiş yazdırma
   • Yenile: Mevcut verilerle yeniden üretir

4. ŞABLONLAR:
   • Formu şablon olarak kaydedebilirsiniz
   • Kayıtlı şablonları tekrar yükleyebilirsiniz
   • Şablonları silebilirsiniz

5. GEÇMİŞ:
   • Ürettiğiniz stratejileri görüntüleyin
   • Geçmişi temizleyebilirsiniz

6. AYARLAR:
   • Dil: TR, EN, DE, FR
   • Tema: Açık, Koyu, Klasik
   • AI Model: DeepSeek veya yerel modeller
   • API Anahtarı: DeepSeek API anahtarınız

💡 İPUÇLARI:
• DeepSeek API için ücretsiz anahtar alabilirsiniz
• İnternet yoksa offline fallback çalışır
• Formu sık kullanılanlar için şablon olarak kaydedin
• Stratejilerinizi düzenli olarak export edin

📞 DESTEK:
• Hata durumunda 'Hata Bildir' kullanın
• Güncellemeler için programı kontrol edin
        """

        help_window = tk.Toplevel(self.root)
        help_window.title("Yardım")
        help_window.geometry("600x500")

        help_text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD)
        help_text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)

    def report_bug(self):
        """Hata bildir"""
        bug_window = tk.Toplevel(self.root)
        bug_window.title("Hata Bildir")
        bug_window.geometry("500x400")

        ttk.Label(bug_window, text="Hata Açıklaması:", font=('Arial', 10, 'bold')).pack(pady=10)

        bug_text = scrolledtext.ScrolledText(bug_window, height=15)
        bug_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Button(bug_window, text="Gönder",
                  command=lambda: self.submit_bug(bug_text.get(1.0, tk.END), bug_window)).pack(pady=10)

    def submit_bug(self, bug_description, window):
        """Hata raporunu gönder (simüle)"""
        if not bug_description.strip():
            messagebox.showwarning("Uyarı", "Lütfen hata açıklaması girin!")
            return

        # Simüle edilmiş gönderim
        print(f"Hata Raporu:\n{bug_description}")
        messagebox.showinfo("Teşekkürler", "Hata raporunuz alındı. Teşekkür ederiz!")
        window.destroy()

    def show_about(self):
        """Hakkında"""
        about_text = f"""
YEREL İŞLETME STRATEJİ MOTORU

Versiyon: {CONFIG['version']}
Geliştirici: Uzman Yazılım Ekibi
Lisans: MIT Open Source

ÖZELLİKLER:
• Yerel işletmeler için AI destekli strateji üretimi
• Çoklu AI entegrasyonu (DeepSeek, Transformers)
• Kapsamlı sektör veritabanı
• Çoklu dil desteği
• Çeşitli export formatları
• Şablon yönetimi
• Geçmiş takibi

AMAÇ:
Yerel işletmelerin dijital dönüşümünü
kolaylaştırmak ve büyümelerine
yardımcı olmak.

İLETİŞİM:
Bu bir açık kaynak projesidir.
Katkılarınızı bekliyoruz!

🔗 GitHub: (proje linki)
📧 E-posta: (iletişim adresi)
        """

        messagebox.showinfo("Hakkında", about_text)

    def setup_auto_save(self):
        """Otomatik kaydetme timer'ı"""
        if hasattr(self, 'auto_save_timer'):
            self.root.after_cancel(self.auto_save_timer)

        def auto_save():
            if self.business_data and self.config_manager.get('auto_save', True):
                # Basit bir otomatik kaydetme
                try:
                    auto_save_file = Path.home() / '.local_business_strategy' / 'autosave.json'
                    auto_save_file.parent.mkdir(parents=True, exist_ok=True)

                    save_data = {
                        'timestamp': datetime.now().isoformat(),
                        'business_data': self.business_data,
                        'strategy': self.strategy_text.get(1.0, tk.END).strip()[:1000]
                    }

                    with open(auto_save_file, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, indent=2, ensure_ascii=False)

                except Exception as e:
                    print(f"Otomatik kaydetme hatası: {e}")

            # Timer'ı yeniden başlat
            self.auto_save_timer = self.root.after(
                CONFIG['auto_save_interval'] * 1000,
                auto_save
            )

        # İlk timer'ı başlat
        self.auto_save_timer = self.root.after(
            CONFIG['auto_save_interval'] * 1000,
            auto_save
        )

def main():
    """Ana fonksiyon"""
    try:
        root = tk.Tk()
        app = StrategyApp(root)

        # Pencereyi merkezle
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')

        root.mainloop()
    except Exception as e:
        print(f"Uygulama başlatılamadı: {e}")
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı:\n\n{str(e)}")

if __name__ == "__main__":
    main()
