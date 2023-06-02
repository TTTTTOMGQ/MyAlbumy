# -*- codeing = utf-8 -*-
from flask import url_for

from albumy import db
from albumy.models import Notification


def push_follow_notification(follower, receiver):
    message = f'User <a href="{url_for("user.index", username=follower.username)}">' \
              f'{follower.username}</a> followed you.'
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_comment_notification(photo_id, receiver, page=1):
    message = f'<a href="{url_for("main.show_photo", photo_id=photo_id, page=page)}#comments">This photo</a>' \
              f' has new comment/reply.'
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_collect_notification(collector, photo_id, receiver):
    message = f'User <a href="{url_for("user.index", username=collector.username)}">"{collector.username}"</a>' \
              f'collected your ' \
              f'<a href="{url_for("main.show_photo", photo_id=photo_id)}">photo</a>'
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()
