# -*- coding: utf-8 -*-
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, AnonymousUserMixin
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_avatars import Avatars
from flask_dropzone import Dropzone
from flask_whooshee import Whooshee
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

bootstrap = Bootstrap()
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
dropzone = Dropzone()
moment = Moment()
avatars = Avatars()
csrf = CSRFProtect()
migrate = Migrate()
whooshee = Whooshee()


# 为了避免循环导入，将login_manager的初始化放在这里
@login_manager.user_loader
def load_user(user_id):
    from albumy.models import User
    user = User.query.get(int(user_id))
    return user


login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'


# guest用户
class Guest(AnonymousUserMixin):
    def can(self, permission_name):
        return False
    
    @property
    def is_admin(self):
        return False


login_manager.anonymous_user = Guest
