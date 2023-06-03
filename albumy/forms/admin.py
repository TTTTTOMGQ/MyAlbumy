# -*- codeing = utf-8 -*-
from wtforms import StringField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, ValidationError

from albumy.models import User, Role
from albumy.forms.user import EditProfileForm


class EditProfileAdminForm(EditProfileForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    role = SelectField('Role', coerce=int)
    # coerce是一个可选参数，其作用是把字段的值转换成指定的类型，这里是int类型
    active = BooleanField('Active')
    confirmed = BooleanField('Confirmed')
    submit = SubmitField('Submit')
    
    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(user, *args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        # self.user设置为user是为了在视图函数中使用
        self.user = user

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')