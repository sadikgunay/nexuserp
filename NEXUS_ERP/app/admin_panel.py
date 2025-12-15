from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from app.extensions import db
from app.models import User, Institution, Item, AssignmentLog, Maintenance, Document, Choice

# --- GÜVENLİK AYARI ---
# Sadece giriş yapmış kullanıcılar admin paneline erişebilir
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        flash("Admin paneline erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for('auth.login'))

# Ana sayfa (Dashboard) güvenliği için
class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))

# --- KURULUM FONKSİYONU ---
def setup_admin(app):
    admin = Admin(app, name='Nexus Yönetim', template_mode='bootstrap4', index_view=SecureAdminIndexView())

    # Modelleri Panele Ekle
    admin.add_view(SecureModelView(Institution, db.session, name="Kurumlar"))
    admin.add_view(SecureModelView(User, db.session, name="Kullanıcılar"))
    admin.add_view(SecureModelView(Item, db.session, name="Demirbaşlar"))
    admin.add_view(SecureModelView(Choice, db.session, name="Seçenekler"))
    admin.add_view(SecureModelView(AssignmentLog, db.session, name="Loglar"))
    admin.add_view(SecureModelView(Maintenance, db.session, name="Bakımlar"))
    admin.add_view(SecureModelView(Document, db.session, name="Belgeler"))