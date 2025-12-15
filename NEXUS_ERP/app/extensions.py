from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Veritabanı ve Login Yöneticisi
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Lütfen giriş yapınız."
login_manager.login_message_category = "warning"