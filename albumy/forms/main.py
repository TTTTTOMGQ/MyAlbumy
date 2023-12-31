# -*- codeing = utf-8 -*-
from flask_wtf import FlaskForm as _FlaskForm
from wtforms import TextAreaField, SubmitField, StringField
from wtforms.validators import Optional, Length, DataRequired


class FlaskForm(_FlaskForm):
    def validate_on_submit(self, extra_validators=None):
        return self.is_submitted() and self.validate()


class DescriptionForm(FlaskForm):
    description = TextAreaField('Description', validators=[Optional(), Length(0, 500)])
    submit = SubmitField()


class TagForm(FlaskForm):
    # Optional()表示这个字段是可选的，不填写也可以
    tag = StringField('Add Tag (use space to separate)', validators=[Optional(), Length(0, 64)])
    submit = SubmitField()


class CommentForm(FlaskForm):
    body = TextAreaField('', validators=[DataRequired(), Length(1, 128)])
    submit = SubmitField()
