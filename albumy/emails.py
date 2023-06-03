# -*- codeing = utf-8 -*-
from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from albumy.extensions import mail


def _send_async_mail(app, message):
    # 此方法作用是在新的线程中发送邮件
    with app.app_context():
        # app_context()方法将app推入栈中，使其成为当前线程的代理对象
        mail.send(message)


def send_mail(to, subject, template, **kwargs):
    message = Message(current_app.config['ALBUMY_MAIL_SUBJECT_PREFIX'] + subject, recipients=[to])
    # recipients:收件人列表 subject:邮件主题
    message.body = render_template(template + '.txt', **kwargs)
    message.html = render_template(template + '.html', **kwargs)
    app = current_app._get_current_object()
    # current_app是一个代理对象，需要使用_get_current_object()方法获取真实的app对象
    thr = Thread(target=_send_async_mail, args=[app, message])
    thr.start()
    return thr


def send_confirm_email(user, token, to=None):
    send_mail(subject='Confirm Your Account',
              to=to or user.email,
              user=user,
              token=token,
              template='emails/confirm')


def send_reset_password_email(user, token):
    send_mail(subject='Reset Your Password',
              to=user.email,
              token=token,
              template='emails/reset_password')


def send_change_email_email(user, token, to=None):
    send_mail(subject='Change Your Email',
              to=to or user.email,
              user=user,
              token=token,
              template='emails/change_email')
