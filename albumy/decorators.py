# -*- codeing = utf-8 -*-
from functools import wraps

from flask import url_for, flash, redirect, abort
from flask_login import current_user
from markupsafe import Markup


# 确认账户装饰器
def confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.confirmed:
            message = Markup(
                'Please confirm your account first. '
                'Not receive the email? '
                f'<a class="alert-link" href="{url_for("auth.resend_confirm_email")}">Resend Confirm Email</a>'
            )
            # Markup类用于标记字符串，例如：如果不使用Markup类，那么<a>标签就会被转义，从而导致<a>标签失效
            flash(message, 'warning')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    
    return decorated_function


# 权限验证装饰器
def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission_name):
                abort(403)
            return func(*args, **kwargs)
        
        return decorated_function
    
    return decorator


# 管理员权限验证装饰器
def admin_required(func):
    return permission_required('ADMINISTER')(func)
