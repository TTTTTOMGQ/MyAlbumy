# -*- codeing = utf-8 -*-
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, FileField, HiddenField, PasswordField, BooleanField
from wtforms.validators import Length, DataRequired, Regexp, Optional, URL, ValidationError, EqualTo, Email

from albumy.models import User


class EditProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
    username = StringField('Username',
                           validators=[DataRequired(),
                                       Length(1, 20),
                                       Regexp('^[a-zA-Z0-9]*$',
                                              message='The username should contain only a-z, A-Z and 0-9.')])
    website = StringField('Website', validators=[Optional(), URL(), Length(0, 255)])
    location = StringField('Location', validators=[Optional(), Length(0, 50)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(0, 120)])
    submit = SubmitField()
    
    def validate_username(self, field):
        if field.data != current_user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('The username is already in use.')


class UploadAvatarForm(FlaskForm):
    image = FileField('Upload',
                      validators=[FileRequired(),
                                  FileAllowed(['jpg', 'png '], 'Only images are accepted.')])
    submit = SubmitField()


class CropAvatarForm(FlaskForm):
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField()


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired(), Length(8, 128)])
    password = PasswordField('New password', validators=[DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField('Confirm new password', validators=[DataRequired()])
    submit = SubmitField()
    
class ChangeEmailForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField()
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('The email is already in use.')


class NotificationSettingForm(FlaskForm):
    receive_comment_notification = BooleanField('New comment')
    receive_follow_notification = BooleanField('New follower')
    receive_collect_notification = BooleanField('New collector')
    submit = SubmitField()


class PrivacySettingForm(FlaskForm):
    public_collections = BooleanField('Public my collections')
    submit = SubmitField()
    
class DeleteAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    submit = SubmitField()
    
    # 该方法是在jinjia2模板中调用的，用于验证表单中的username字段是否与当前用户的username相同
    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError('Wrong username.')
