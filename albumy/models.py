# -*- codeing = utf-8 -*-
import os
from datetime import datetime

from flask import current_app
from flask_avatars import Identicon
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from albumy.extensions import db, whooshee

roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
                             )

tagging = db.Table('tagging',
                   db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                   )


class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # follower 指的是粉丝，followed指的是关注的人
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following', lazy='joined')
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers', lazy='joined')

@whooshee.register_model('name', 'username')
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, index=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(30))
    website = db.Column(db.String(255))
    bio = db.Column(db.String(120))
    location = db.Column(db.String(50))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64))
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    locked = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    
    role = db.relationship('Role', back_populates='users')
    photos = db.relationship('Photo', back_populates='author', cascade='all')
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    comments = db.relationship('Comment', back_populates='author', cascade='all')
    # following是正在关注的人，followers是关注自己的人
    following = db.relationship('Follow', foreign_keys=[Follow.follower_id], back_populates='follower', lazy='dynamic',
                                cascade='all')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], back_populates='followed', lazy='dynamic',
                                cascade='all')
    
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')
    receive_comments_notifications = db.Column(db.Boolean, default=True)
    receive_follow_notifications = db.Column(db.Boolean, default=True)
    receive_collect_notifications = db.Column(db.Boolean, default=True)
    
    show_collections = db.Column(db.Boolean, default=True)
    
    @property
    def is_admin(self):
        return self.role.name == 'Administrator'

    @property
    def is_active(self):
        return self.active

    def __init__(self, **kwargs):
        # super内的 User可以不用写，但是必须写self
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        self.set_role()
        self.follow(self)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_role(self):
        if self.role is None:
            if self.email == current_app.config('ALBUMY_ADMIN_EMAIL'):
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()
    
    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()
    
    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and \
            self.role is not None and \
            permission in self.role.permissions
    
    def collect(self, photo):
        if not self.is_collecting(photo):
            collect = Collect(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()
    
    def uncollect(self, photo):
        collect = Collect.collected.filter_by(collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()
    
    def is_collecting(self, photo):
        return self.collected.filter_by(photo_id=photo.id).first is not None
    
    def follow(self, user):
        if not self.is_following(user):
            # 设置被关注者为user，关注者为self
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()
    
    def unfollow(self, user):
        follow = self.followed.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()
    
    def is_following(self, user):
        return self.following.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None
    
    def lock(self):
        self.locked = True
        self.role = Role.query.filter_by(name='locked').first()
        db.session.commit()
    
    def unlock(self):
        self.locked = False
        self.set_role()
    
    def block(self):
        self.active = False
        db.session.commit()
    
    def unblock(self):
        self.active = True
        db.session.commit()
    
    @staticmethod
    def init_role_permission():
        for user in User.query.all():
            if user.role is None:
                if user.email == current_app.config['ALBUMY_ADMIN_EMAIL']:
                    user.role = Role.query.filter_by(name='Administrator').first()
                else:
                    user.role = Role.query.filter_by(name='User').first()
            db.session.add(user)
        db.session.commit()


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    # back_populates为什么是roles，而不是role呢？因为这里的roles是一个列表，而不是一个对象
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')
    users = db.relationship('User', back_populates='role')
    
    @staticmethod
    def init_role():
        roles_permissions_map = {
            'Locked': ['FOLLOW', 'COLLECT'],
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],
            'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER']
        }
        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            # role本身没有permissions属性，但是有一个permissions的关系属性，这个属性是一个列表,至于为什么是列表，因为这个属性是一个多对多的关系，所以是一个列表
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')

@whooshee.register_model('description')
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    filename_m = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    can_comment = db.Column(db.Boolean, default=True)
    flag = db.Column(db.Integer, default=0)
    
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', back_populates='photos')
    comments = db.relationship('Comment', back_populates='photo', cascade='all')
    
    tags = db.relationship('Tag', back_populates='photos', secondary=tagging)
    
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')
    
    @property
    def collectors_count(self):
        return len(self.collectors)

@whooshee.register_model('naem')
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    photos = db.relationship('Photo', back_populates='tags', secondary=tagging)


class Collect(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('photo.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    collector = db.relationship('User', back_populates='collections', lazy='joined')
    # lazy设为joined的意思是，当我们查询一个收藏记录的时候，会同时查询出这个收藏记录对应的用户，这样就不用再写一条查询语句了
    collected = db.relationship('Photo', back_populates='collectors', lazy='joined')
    # lazy设为joined的意思是，当我们查询一个收藏记录的时候，会同时查询出这个收藏记录对应的图片，这样就不用再写一条查询语句了


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    # flag是一个标志位，如果flag为0，表示这条评论是正常的，如果flag为1，表示这条评论是被删除的
    flag = db.Column(db.Integer, default=0)
    
    replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    
    photo = db.relationship('Photo', back_populates='comments')
    author = db.relationship('User', back_populates='comments')
    # cascade='all'的意思是，当我们删除一个评论的时候，会把这个评论的回复也删除掉
    replied = db.relationship('Comment', back_populates='replies', cascade='all')
    # remote_side=[id]的意思是，这个replied属性指向的是Comment表中的id字段
    replies = db.relationship('Comment', back_populates='replied', remote_side=[id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver = db.relationship('User', back_populates='notifications')


@db.event.listens_for(Photo, 'after_delete', named=True)  # 这里的named=True是为了让target这个参数可以被传入
def delete_photo(**kwargs):
    target = kwargs['target']
    for filename in [target.filename, target.filename_s, target.filename_m]:
        if filename is not None:
            path = os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename)
            if os.path.exists(path):
                os.remove(path)


@db.event.listens_for(User, 'after_delete', named=True)
def delete_avatar(**kwargs):
    target = kwargs['target']
    for filename in [target.avatar_s, target.avatar_m, target.avatar_l, target.avatar_raw]:
        if filename is not None:
            path = os.path.join(current_app.config['AVATARS_SAVE_PATH'], filename)
            if os.path.exists(path):
                os.remove(path)



