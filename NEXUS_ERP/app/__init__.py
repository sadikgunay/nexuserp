import os
from flask import Flask
from app.extensions import db, login_manager
# --- YENİ EKLENEN SATIR 1 ---
from app.admin_panel import setup_admin

def create_app():
    app = Flask(__name__)

    # --- AYARLAR ---
    app.config['SECRET_KEY'] = 'bu-cok-gizli-bir-anahtardir'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'postgresql://nexus_user:nexus_password@nexus_db:5432/nexus_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- DOSYA YÜKLEME AYARI ---
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # --- BAŞLATMA ---
    db.init_app(app)
    login_manager.init_app(app)

    # --- MODELLER ---
    from app import models

    # --- ADMIN PANELİNİ BAŞLAT (YENİ EKLENEN SATIR 2) ---
    setup_admin(app)

    # --- BLUEPRINTLER ---
    try:
        from app.routes.main import main_bp
        from app.routes.inventory import inventory_bp
        from app.routes.auth import auth_bp
        from app.routes.settings import settings_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(inventory_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(settings_bp)
    except ImportError:
        pass

    with app.app_context():
        db.create_all()

    return app