from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Choice
from app.extensions import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def index():
    # Sadece kullanıcının kurumuna ait seçenekleri getir
    choices = Choice.query.filter_by(institution_id=current_user.institution_id).all()
    
    data = {
        'brands': [c for c in choices if c.type == 'brand'],
        'categories': [c for c in choices if c.type == 'category'],
        'departments': [c for c in choices if c.type == 'department'],
        'locations': [c for c in choices if c.type == 'location'],
        'vendors': [c for c in choices if c.type == 'vendor']
    }
    return render_template('pages/settings.html', data=data)

@settings_bp.route('/settings/add', methods=['POST'])
@login_required
def add_choice():
    type_key = request.form.get('type')
    name = request.form.get('name')
    
    if type_key and name:
        # YENİ: Eklerken kurum ID'sini de kaydediyoruz
        new_choice = Choice(
            type=type_key, 
            name=name,
            institution_id=current_user.institution_id
        )
        db.session.add(new_choice)
        db.session.commit()
        flash('Eklendi.', 'success')
    else:
        flash('Hata: Bilgiler eksik.', 'danger')
        
    return redirect(url_for('settings.index'))

@settings_bp.route('/settings/delete/<int:id>', methods=['POST'])
@login_required
def delete_choice(id):
    # Silmeye çalışılan veri bu kuruma mı ait? Kontrol et.
    choice = Choice.query.filter_by(id=id, institution_id=current_user.institution_id).first_or_404()
    
    db.session.delete(choice)
    db.session.commit()
    flash('Silindi.', 'success')
    return redirect(url_for('settings.index'))