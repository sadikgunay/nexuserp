import io
import os
import qrcode
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
import pandas as pd
from app.models import Item, AssignmentLog, Maintenance, Document, Choice
from app.extensions import db

inventory_bp = Blueprint('inventory', __name__)

# --- YARDIMCI FONKSİYONLAR ---
def parse_date(date_str):
    if not date_str: return None
    try: return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError: return None

def safe_float(value):
    if not value: return 0.0
    try: return float(value.replace(',', '.'))
    except ValueError: return 0.0

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_dropdowns():
    """
    Sadece kullanıcının bağlı olduğu kuruma (institution_id) ait seçenekleri getirir.
    """
    # EĞER modeller güncellenmediyse hata vermemesi için try-except veya kontrol eklenebilir
    # Ancak mantıken Choice modelinde de institution_id olması gerekir.
    
    # Sadece kullanıcının kurumuna ait seçenekleri çekiyoruz
    if hasattr(Choice, 'institution_id'):
        choices = Choice.query.filter_by(institution_id=current_user.institution_id).all()
    else:
        # Geçici uyumluluk (Choice tablosunda henüz institution_id yoksa hepsi gelir)
        choices = Choice.query.all()
    
    # Veritabanı o kurum için boşsa varsayılanları döndür
    if not choices:
        return {
            'brands': ['Apple', 'Dell', 'HP', 'Lenovo'],
            'categories': ['Laptop', 'Monitör', 'Telefon'],
            'departments': ['IT', 'İK', 'Muhasebe'],
            'locations': ['Merkez', 'Depo'],
            'vendors': ['Amazon', 'MediaMarkt']
        }

    return {
        'brands': [c.name for c in choices if c.type == 'brand'],
        'categories': [c.name for c in choices if c.type == 'category'],
        'departments': [c.name for c in choices if c.type == 'department'],
        'locations': [c.name for c in choices if c.type == 'location'],
        'vendors': [c.name for c in choices if c.type == 'vendor']
    }

# --- LİSTELEME VE FİLTRELEME ---
@inventory_bp.route('/inventory')
@login_required
def index():
    f_category = request.args.get('category')
    f_status = request.args.get('status')
    f_department = request.args.get('department')
    f_search = request.args.get('search')

    # KRİTİK DEĞİŞİKLİK: Sorguyu kurum ID'sine göre başlatıyoruz.
    # Kullanıcı sadece kendi kurumunun verilerini görebilir.
    query = Item.query.filter_by(institution_id=current_user.institution_id)

    if f_category:
        query = query.filter(Item.category == f_category)
    if f_status:
        query = query.filter(Item.status == f_status)
    if f_department:
        query = query.filter(Item.department == f_department)
    if f_search:
        search_term = f"%{f_search}%"
        query = query.filter(or_(
            Item.name.ilike(search_term),
            Item.serial_no.ilike(search_term),
            Item.assigned_to.ilike(search_term)
        ))

    items = query.order_by(Item.id.desc()).all()

    stats = {
        'total_items': len(items),
        'total_value': sum(item.price or 0 for item in items),
        'assigned_count': sum(1 for item in items if item.assigned_to),
        'broken_count': sum(1 for item in items if item.status in ['Arızalı', 'Hurda'])
    }

    return render_template('pages/inventory.html', 
                           items=items, 
                           dropdowns=get_dropdowns(), 
                           stats=stats)

# --- ÜRÜN EKLEME ---
@inventory_bp.route('/add', methods=['POST'])
@login_required
def add_item():
    try:
        new_item = Item(
            name=request.form.get('name'),
            category=request.form.get('category'),
            brand=request.form.get('brand'),
            model=request.form.get('model'),
            serial_no=request.form.get('serial_no') or None,
            asset_tag=request.form.get('asset_tag') or None,
            status=request.form.get('status'),
            price=safe_float(request.form.get('price')),
            currency=request.form.get('currency'),
            vendor=request.form.get('vendor'),
            purchase_date=parse_date(request.form.get('purchase_date')),
            warranty_date=parse_date(request.form.get('warranty_date')),
            assigned_to=request.form.get('assigned_to'),
            department=request.form.get('department'),
            location=request.form.get('location'),
            notes=request.form.get('notes'),
            added_by=current_user.username,
            # KRİTİK DEĞİŞİKLİK: Ürünü ekleyen kullanıcının kurum ID'si kaydedilir.
            institution_id=current_user.institution_id 
        )
        db.session.add(new_item)
        db.session.commit()
        
        log = AssignmentLog(item_id=new_item.id, action="Oluşturuldu", details=f"{current_user.username} ekledi.", performed_by=current_user.username)
        db.session.add(log)
        db.session.commit()

        flash('Ürün başarıyla eklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'danger')
    return redirect(url_for('inventory.index'))

# --- DETAY SAYFASI ---
@inventory_bp.route('/item/<int:id>')
@login_required
def item_details(id):
    # GÜVENLİK: Sadece ID ile çekmek yetmez, kurum ID'si de eşleşmeli.
    # Başka kurumun ürününe URL'den ID yazarak erişemesinler.
    item = Item.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    
    return render_template('pages/item_details.html', item=item, logs=item.logs, dropdowns=get_dropdowns())

# --- DETAYLI DÜZENLEME ---
@inventory_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit_item(id):
    # GÜVENLİK KONTROLÜ
    item = Item.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    
    try:
        old_status = item.status
        old_user = item.assigned_to

        # Tüm alanları güncelle
        item.name = request.form.get('name')
        item.category = request.form.get('category')
        item.brand = request.form.get('brand')
        item.model = request.form.get('model')
        item.serial_no = request.form.get('serial_no')
        item.asset_tag = request.form.get('asset_tag')
        
        item.price = safe_float(request.form.get('price'))
        item.currency = request.form.get('currency')
        item.vendor = request.form.get('vendor')
        item.purchase_date = parse_date(request.form.get('purchase_date'))
        item.warranty_date = parse_date(request.form.get('warranty_date'))
        
        item.assigned_to = request.form.get('assigned_to')
        item.department = request.form.get('department')
        item.location = request.form.get('location')
        item.status = request.form.get('status')
        item.notes = request.form.get('notes')
        
        db.session.commit()

        # Loglar
        if old_status != item.status:
            db.session.add(AssignmentLog(item_id=item.id, action="Durum Değişti", details=f"{old_status} -> {item.status}", performed_by=current_user.username))
        
        if old_user != item.assigned_to:
            db.session.add(AssignmentLog(item_id=item.id, action="Zimmet Değişti", details=f"{old_user or 'Depo'} -> {item.assigned_to or 'Depo'}", performed_by=current_user.username))
            
        db.session.commit()
        flash('Bilgiler güncellendi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    return redirect(url_for('inventory.item_details', id=id))

# --- SİLME ---
@inventory_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    # GÜVENLİK KONTROLÜ
    item = Item.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    
    db.session.delete(item)
    db.session.commit()
    flash('Silindi.', 'success')
    return redirect(url_for('inventory.index'))

# --- QR & TUTANAK ---
@inventory_bp.route('/qr/<int:id>')
@login_required
def generate_qr(id):
    # QR kod oluştururken de erişim kontrolü yapıyoruz (Opsiyonel ama güvenli)
    item = Item.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    
    url = url_for('inventory.item_details', id=id, _external=True)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@inventory_bp.route('/print-handover/<int:id>')
@login_required
def print_handover(id):
    item = Item.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    return render_template('pages/print_handover.html', item=item, date=datetime.now().strftime('%d.%m.%Y'))

# --- BAKIM (MAINTENANCE) ---
@inventory_bp.route('/maintenance/add/<int:item_id>', methods=['POST'])
@login_required
def add_maintenance(item_id):
    try:
        # GÜVENLİK KONTROLÜ
        item = Item.query.filter_by(id=item_id, institution_id=current_user.institution_id).first_or_404()
        
        maintenance = Maintenance(
            item_id=item.id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            cost=safe_float(request.form.get('cost')),
            performed_by=request.form.get('performed_by'),
            date=parse_date(request.form.get('date')) or datetime.now().date(),
            # Bakım tablosunda institution_id tutmuyorsan gerek yok, item üzerinden erişilir. 
            # Ancak tutuyorsan buraya ekle: institution_id=current_user.institution_id
        )
        db.session.add(maintenance)
        
        log = AssignmentLog(item_id=item.id, action="Bakım Kaydı", details=f"{request.form.get('title')} - {request.form.get('cost')} TL", performed_by=current_user.username)
        db.session.add(log)
        
        db.session.commit()
        flash('Bakım kaydı eklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'danger')
    return redirect(url_for('inventory.item_details', id=item_id))

@inventory_bp.route('/maintenance/delete/<int:m_id>', methods=['POST'])
@login_required
def delete_maintenance(m_id):
    # Maintenance tablosundan item'a, item'dan kuruma ulaşıp kontrol ediyoruz
    maintenance = Maintenance.query.get_or_404(m_id)
    item = Item.query.get(maintenance.item_id)
    
    if item.institution_id != current_user.institution_id:
        abort(403) # Yetkisiz erişim
        
    try:
        db.session.delete(maintenance)
        db.session.commit()
        flash('Bakım kaydı silindi.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {e}', 'danger')
    return redirect(url_for('inventory.item_details', id=item.id))

# --- BELGE (DOCUMENTS) ---
@inventory_bp.route('/document/upload/<int:item_id>', methods=['POST'])
@login_required
def upload_document(item_id):
    item = Item.query.filter_by(id=item_id, institution_id=current_user.institution_id).first_or_404()
    
    if 'file' not in request.files:
        flash('Dosya seçilmedi.', 'danger')
        return redirect(url_for('inventory.item_details', id=item_id))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Dosya ismi boş.', 'danger')
        return redirect(url_for('inventory.item_details', id=item_id))

    if file and allowed_file(file.filename):
        try:
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + original_filename
            
            # Kuruma özel klasörleme yapılabilir ama şimdilik ortak klasörde isimle ayırıyoruz
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            doc = Document(item_id=item.id, filename=filename)
            db.session.add(doc)
            
            db.session.add(AssignmentLog(item_id=item.id, action="Dosya Yüklendi", details=f"{original_filename}", performed_by=current_user.username))
            
            db.session.commit()
            flash('Dosya yüklendi.', 'success')
        except Exception as e:
            flash(f'Yükleme hatası: {e}', 'danger')
    else:
        flash('İzin verilmeyen dosya türü.', 'warning')
    return redirect(url_for('inventory.item_details', id=item_id))

@inventory_bp.route('/document/download/<filename>')
@login_required
def download_document(filename):
    # Dosya indirme güvenliği için de kontrol gerekir
    # Önce dosyanın hangi item'a ait olduğunu bul
    doc = Document.query.filter_by(filename=filename).first_or_404()
    item = Item.query.get(doc.item_id)
    
    if item.institution_id != current_user.institution_id:
        abort(403)

    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@inventory_bp.route('/document/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    item = Item.query.get(doc.item_id)
    
    if item.institution_id != current_user.institution_id:
        abort(403)
        
    filename = doc.filename
    try:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(doc)
        
        db.session.add(AssignmentLog(item_id=item.id, action="Dosya Silindi", details=f"{filename}", performed_by=current_user.username))
        
        db.session.commit()
        flash('Dosya silindi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    return redirect(url_for('inventory.item_details', id=item.id))

# --- EXCEL DIŞA AKTARMA (EXPORT) ---
@inventory_bp.route('/inventory/export')
@login_required
def export_inventory():
    f_category = request.args.get('category')
    f_status = request.args.get('status')
    f_department = request.args.get('department')
    f_search = request.args.get('search')

    # KRİTİK DEĞİŞİKLİK: Sadece kullanıcının kurumuna ait veriler
    query = Item.query.filter_by(institution_id=current_user.institution_id)

    # 2. Filtreleri Uygula
    if f_category:
        query = query.filter(Item.category == f_category)
    if f_status:
        query = query.filter(Item.status == f_status)
    if f_department:
        query = query.filter(Item.department == f_department)
    if f_search:
        search_term = f"%{f_search}%"
        query = query.filter(or_(
            Item.name.ilike(search_term),
            Item.serial_no.ilike(search_term),
            Item.assigned_to.ilike(search_term)
        ))

    items = query.order_by(Item.id.desc()).all()

    # 3. Veriyi Pandas DataFrame'e Çevir
    data = []
    for item in items:
        data.append({
            'ID': item.id,
            'Ürün Adı': item.name,
            'Marka': item.brand,
            'Model': item.model,
            'Seri No': item.serial_no,
            'Kategori': item.category,
            'Durum': item.status,
            'Zimmetli Kişi': item.assigned_to,
            'Departman': item.department,
            'Lokasyon': item.location,
            'Fiyat': item.price,
            'Para Birimi': item.currency,
            'Satın Alma Tarihi': item.purchase_date,
            'Garanti Bitiş': item.warranty_date,
            'Tedarikçi': item.vendor,
            'Ekleyen': item.added_by
        })

    # Veri yoksa boş excel gönder hatayı önle
    if not data:
        df = pd.DataFrame(columns=['ID', 'Ürün Adı', '...']) # Boş
    else:
        df = pd.DataFrame(data)

    output = io.BytesIO()
    # openpyxl kurulu olmalı: pip install openpyxl
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Demirbaş Listesi')
    
    output.seek(0)
    
    filename = f"Envanter_Raporu_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )