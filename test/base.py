# -*- codeing = utf-8 -*-
import unittest

from flask import url_for

from albumy import create_app
from albumy.extensions import db
from albumy.models import Role, User, Photo, Comment, Tag


class BaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app('testing')
        self.context = app.test_request_context()
        self.context.push()
        self.client = app.test_client(use_cookies=True)
        # use_cookies=True:使用cookie模拟客户端
        self.runner = app.test_cli_runner()
        
        db.create_all()
        Role.init_role()
        
        admin_user = User(email='admin@helloflask.com', name='Admin', username='admin', confirmed=True)
        admin_user.set_password('123456')
        
        normal_user = User(email='normal@helloflask.com', name='Normal User', username='normal', confirmed=True)
        normal_user.set_password('123456')
        
        unconfirmed_user = User(email='unconfirmed@helloflask.com', name='Unconfirmed', username='unconfirmed',
                                confirmed=False)
        unconfirmed_user.set_password('123456')
        
        locked_user = User(email='locked@helloflask.com', name='Locked User', username='locked',
                           confirmed=True, locked=True)
        locked_user.set_password('123456')
        locked_user.lock()
        
        blocked_user = User(email='blocked@helloflask.com', name='Blocked User', username='blocked',
                            confirmed=True, active=False)
        blocked_user.set_password('123')
        
        photo = Photo(filename='test.jpg', filename_s='test_s.jpg', filename_m='test_m.jpg',
                      description='Photo 1', author=admin_user)
        photo2 = Photo(filename='test2.jpg', filename_s='test_s2.jpg', filename_m='test_m2.jpg',
                       description='Photo 2', author=normal_user)
        
        comment = Comment(body='test comment body', photo=photo, author=normal_user)
        
        tag = Tag(name='test tag')
        
        photo.tags.append(tag)
        
        db.session.add_all([admin_user, normal_user, unconfirmed_user, locked_user, blocked_user])
        db.session.commit()
    
    def tearDown(self) -> None:
        db.drop_all()
        self.context.pop()
    
    def login(self, email=None, password=None):
        if email is None and password is None:
            email = 'normal@helloflask.com'
            password = '123456'
        
        return self.client.post(url_for('auth.login'), data=dict(
            email=email,
            password=password
        ), follow_redirects=True)
    
    def logout(self):
        return self.client.get(url_for('auth.logout'), follow_redirects=True)
