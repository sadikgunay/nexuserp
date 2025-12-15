from app.extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime

# --- KULLANICI YÜKLEYİCİ ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- KURUM MODELİ (YENİ) ---
class Institution(db.Model):
    __tablename__ = 'institutions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150)) # Opsiyonel: Kurum Adı (Örn: ABC Lojistik)
    code = db.Column(db.String(50), unique=True, nullable=False) # Kurum Kodu (Benzersiz)
    password_hash = db.Column(db.String(512), nullable=False) # Kurum Şifresi

    # İlişkiler
    users = db.relationship('User', backref='institution', lazy=True)
    items = db.relationship('Item', backref='institution', lazy=True)
    choices = db.relationship('Choice', backref='institution', lazy=True)

# --- KULLANICI MODELİ ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), default='Yönetici') 
    email = db.Column(db.String(150), unique=True, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    
    # Hangi kuruma ait?
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'

# --- DEMİRBAŞ (ITEM) MODELİ ---
class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    
    # Kimlik Bilgileri
    name = db.Column(db.String(200), nullable=False, index=True)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_no = db.Column(db.String(100), index=True) # Unique kaldırıldı, farklı firmalarda aynı seri no olabilir.
    asset_tag = db.Column(db.String(100)) # Unique kaldırıldı.
    category = db.Column(db.String(100), index=True)
    status = db.Column(db.String(50), default='Aktif', index=True)
    
    # Finansal Bilgiler
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='TL')
    vendor = db.Column(db.String(150))
    purchase_date = db.Column(db.Date)
    warranty_date = db.Column(db.Date)
    
    # Lokasyon Bilgileri
    assigned_to = db.Column(db.String(150))
    department = db.Column(db.String(100))
    location = db.Column(db.String(150))
    
    # Diğer
    notes = db.Column(db.Text)
    added_by = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # KURUM BAĞLANTISI (YENİ)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)

    # İlişkiler
    logs = db.relationship('AssignmentLog', backref='item', lazy=True, cascade="all, delete-orphan")
    maintenances = db.relationship('Maintenance', backref='item', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('Document', backref='item', lazy=True, cascade="all, delete-orphan")

# --- LOG MODELİ ---
class AssignmentLog(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    action = db.Column(db.String(100))
    details = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(150))

# --- BAKIM MODELİ ---
class Maintenance(db.Model):
    __tablename__ = 'maintenances'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    title = db.Column(db.String(200))
    date = db.Column(db.Date)
    description = db.Column(db.Text)
    cost = db.Column(db.Float, default=0.0)
    performed_by = db.Column(db.String(100))

# --- DOKÜMAN MODELİ ---
class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- AYARLAR / SEÇENEKLER MODELİ ---
class Choice(db.Model):
    __tablename__ = 'choices'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, index=True) # brand, category, etc.
    name = db.Column(db.String(100), nullable=False)
    
    # KURUM BAĞLANTISI (YENİ - Her kurumun departmanları farklıdır)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    
    def __repr__(self):
        return f'<Choice {self.type}: {self.name}>'