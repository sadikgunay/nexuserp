from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Item

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Veritabanından SADECE BU KURUMA AİT Ürünleri Çek
    try:
        # --- ÇOKLU KİRACI FİLTRESİ ---
        # Kullanıcı hangi kurumdaysa sadece o kurumun ürünlerini görür.
        items = Item.query.filter_by(institution_id=current_user.institution_id).all()
        print(f"--- DEBUG: Kurum ID {current_user.institution_id} için {len(items)} adet ürün çekildi ---")
    except Exception as e:
        print(f"--- HATA: Veritabanı okunamadı: {e} ---")
        items = []

    today = date.today()
    
    # 2. Temel Sayaçlar
    total_count = len(items)
    # Fiyatı None olanları 0 sayarak topla
    total_investment = sum((item.price if item.price is not None else 0.0) for item in items)
    
    # 3. Grafik ve Liste Verilerini Hazırla
    status_counts = {}   # Örn: {'Aktif': 5, 'Hurda': 2}
    dept_stats = {}      # Örn: {'IT': 3, 'İK': 1}
    warranty_alerts = [] # Yaklaşan garantiler listesi
    expired_count = 0    # Garantisi bitmiş cihaz sayısı

    for item in items:
        # --- Durum Analizi ---
        s_status = item.status if item.status else "Belirsiz"
        status_counts[s_status] = status_counts.get(s_status, 0) + 1
        
        # --- Departman Analizi ---
        d_dept = item.department if item.department else "Atanmamış"
        dept_stats[d_dept] = dept_stats.get(d_dept, 0) + 1 
        
        # --- Garanti Kontrolü ---
        if item.warranty_date:
            try:
                days_left = (item.warranty_date - today).days
                if days_left < 0:
                    expired_count += 1
                elif days_left <= 30: # 30 günden az kalanları listeye ekle
                    warranty_alerts.append({
                        'name': item.name,
                        'days': days_left,
                        'date': item.warranty_date.strftime('%Y-%m-%d')
                    })
            except Exception as e: 
                print(f"Tarih Hatası (ID: {item.id}): {e}")

    # Konsola yazdıralım (Hata ayıklamak için)
    print(f"DEBUG: Durum Verisi -> {status_counts}")
    print(f"DEBUG: Departman Verisi -> {dept_stats}")

    # 4. Verileri HTML'e Gönder
    return render_template(
        'pages/dashboard.html',
        page_title=f"Yönetim Paneli - {current_user.institution.code}", # Başlıkta kurum kodu yazar
        
        # Kartlar için
        total_count=total_count,
        total_value="{:,.2f}".format(total_investment),
        expired_count=expired_count,
        
        # Grafikler için
        chart_status_labels=list(status_counts.keys()),
        chart_status_values=list(status_counts.values()),
        
        chart_dept_labels=list(dept_stats.keys()),
        chart_dept_values=list(dept_stats.values()),
        
        # Alt Liste
        warranty_alerts=warranty_alerts
    )