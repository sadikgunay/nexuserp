from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Institution
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

# --- GİRİŞ YAP ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Kullanıcıyı bul
        user = User.query.filter_by(username=username).first()

        # Sadece şifre kontrolü yeterli, çünkü kullanıcı zaten bir kuruma bağlı
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Hatalı kullanıcı adı veya şifre.', 'danger')
            
    return render_template('auth/login.html')

# --- KAYIT OL (ÖNEMLİ DEĞİŞİKLİK) ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Kullanıcı hem kendi bilgilerini hem de bağlanacağı/oluşturacağı 
    Kurumun bilgilerini (ID ve Şifre) girer.
    """
    if request.method == 'POST':
        # 1. Kişisel Bilgiler
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 2. Kurum Bilgileri
        inst_code = request.form.get('institution_code') # HTML'de name='institution_code' olmalı
        inst_pass = request.form.get('institution_pass') # HTML'de name='institution_pass' olmalı
        inst_name = request.form.get('institution_name') # Opsiyonel (Yeni kurumsa)

        # Kontroller
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten kullanımda.', 'warning')
            return redirect(url_for('auth.register'))

        # --- KURUM MANTIĞI ---
        institution = Institution.query.filter_by(code=inst_code).first()
        
        target_institution = None

        if institution:
            # A) Kurum ZATEN VAR -> Şifresini kontrol et ve dahil ol
            if check_password_hash(institution.password_hash, inst_pass):
                target_institution = institution
                flash(f"Mevcut '{institution.code}' kurumuna katılım sağlandı.", 'info')
            else:
                flash('Girdiğiniz Kurum Kodu kayıtlı ancak Kurum Şifresi hatalı!', 'danger')
                return redirect(url_for('auth.register'))
        else:
            # B) Kurum YOK -> Yeni Kurum oluştur
            hashed_inst_pw = generate_password_hash(inst_pass, method='scrypt')
            new_inst = Institution(
                code=inst_code, 
                password_hash=hashed_inst_pw,
                name=inst_name or inst_code
            )
            db.session.add(new_inst)
            db.session.commit() # ID oluşması için commit şart
            target_institution = new_inst
            flash(f"Yeni kurum '{inst_code}' oluşturuldu.", 'success')

        # --- KULLANICIYI OLUŞTUR VE KURUMA BAĞLA ---
        hashed_user_pw = generate_password_hash(password, method='scrypt')
        new_user = User(
            username=username, 
            password=hashed_user_pw,
            institution_id=target_institution.id # KRİTİK NOKTA
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('auth.login'))
            
    return render_template('auth/register.html')

# --- PROFİL GÜNCELLEME ---
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Form verilerini al
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_phone = request.form.get('phone')
        
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')

        # 1. Kullanıcı Adı Güncelleme
        if new_username and new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Bu kullanıcı adı kullanımda.', 'warning')
            else:
                current_user.username = new_username

        # 2. E-Posta Güncelleme
        if new_email and new_email != current_user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email:
                flash('Bu e-posta adresi kullanımda.', 'warning')
            else:
                current_user.email = new_email
        
        # 3. Telefon Güncelleme
        if new_phone != current_user.phone:
            current_user.phone = new_phone

        db.session.commit()

        # 4. Şifre Değiştirme
        if current_pw and new_pw:
            if check_password_hash(current_user.password, current_pw):
                current_user.password = generate_password_hash(new_pw, method='scrypt')
                db.session.commit()
                flash('Profil bilgileri ve şifreniz güncellendi.', 'success')
            else:
                flash('Mevcut şifreniz hatalı. Sadece bilgiler güncellendi.', 'warning')
        else:
            flash('Profil bilgileriniz güncellendi.', 'success')

        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Güvenli çıkış yapıldı.', 'info')
    return redirect(url_for('auth.login'))