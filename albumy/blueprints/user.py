# -*- codeing = utf-8 -*-
from flask import render_template, current_app, request, Blueprint, flash, redirect, url_for
from flask_login import current_user, login_required, fresh_login_required, logout_user

from albumy.emails import send_confirm_email
from albumy.extensions import avatars, db
from albumy.decorators import confirm_required, permission_required
from albumy.forms.user import UploadAvatarForm, CropAvatarForm, ChangePasswordForm, NotificationSettingForm, \
    PrivacySettingForm, DeleteAccountForm, EditProfileForm, ChangeEmailForm
from albumy.models import User, Photo, Collect
from albumy.nitifications import push_follow_notification
from albumy.settings import Operations
from albumy.utils import redirect_back, flash_errors, generate_token, validate_token

user_bp = Blueprint('user', __name__)


@user_bp.route('/<username>')
def index(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.locked and user == current_user and not current_user.is_admin:
        flash('This user is locked.', 'danger')
        return redirect(url_for('main.index'))
    if user == current_user and not current_user.active:
        flash('You has been blocked', 'danger')
        logout_user()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
    pagination = Photo.query.with_parent(user).order_by(Photo.timestamp.desc()).paginate(page, per_page)
    photos = pagination.items
    return render_template('user/index.html', user=user, pagination=pagination, photos=photos)


@user_bp.route('/<username>/collections')
def show_collections(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
    pagination = Collect.query.with_parent(user).order_by(Collect.timestamp.desc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('user/collections.html', user=user, pagination=pagination, collects=collects)


@user_bp.route('/follow/<username>', methods=['POST'])
@login_required
@confirm_required
@permission_required('FOLLOW')
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_following(user):
        flash('You are already following this user.', 'info')
        return render_template('user/index.html', user=user)
    current_user.follow(user)
    flash('User followed.', 'success')
    if current_user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return redirect_back()


@user_bp.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_following(user):
        flash('You are not following this user.', 'info')
        return render_template('user/index.html', user=user)
    current_user.unfollow(user)
    flash('User unfollowed.', 'success')
    return redirect_back()


@user_bp.route('/<username>/followers')
def show_followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_USER_PER_PAGE']
    pagination = user.followers.pagination(page, per_page)
    follows = pagination.items
    return render_template('user/followers.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/<username>/following')
def show_following(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_USER_PER_PAGE']
    pagination = user.followeing.pagination(page, per_page)
    follows = pagination.items
    return render_template('user/followers.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.username = form.username.data
        current_user.website = form.website.data
        current_user.bio = form.bio.data
        current_user.location = form.location.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    form.name.data = current_user.name
    form.username.data = current_user.username
    form.website.data = current_user.website
    form.bio.data = current_user.bio
    form.location.data = current_user.location
    return render_template('user/settings/edit_profile.html', form=form)


@user_bp.route('/settings/avatar')
@login_required
@confirm_required
def change_avatar():
    upload_form = UploadAvatarForm()
    crop_form = CropAvatarForm()
    return render_template('user/settings/change_avatar.html', upload_form=upload_form, crop_form=crop_form)


@user_bp.route('/settings/avatar/upload', methods=['POST'])
@login_required
@confirm_required
def upload_avatar():
    form = UploadAvatarForm()
    if form.validate_on_submit():
        image = form.image.data
        filename = avatars.save_avatar(image)
        current_user.avatar_raw = filename
        db.session.commit()
    flash_errors(form)
    return redirect(url_for('user.change_avatar'))


@user_bp.route('/settings/avatar/crop', methods=['POST'])
@login_required
@confirm_required
def crop_avatar():
    form = CropAvatarForm()
    if form.validate_on_submit():
        x = form.x.data
        y = form.y.data
        w = form.w.data
        h = form.h.data
        filename = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
        current_user.avatar_s, current_user.avatar_m, current_user.avatar_l = filename
        
        db.session.commit()
        flash('Avatar uploaded.', 'success')
    flash_errors(form)
    return redirect(url_for('user.change_avatar'))


@user_bp.route('/settings/change-password', methods=['GET', 'POST'])
@fresh_login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.commit()
            flash('Password updated.', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.', 'warning')
    return render_template('user/settings/change_password.html', form=form)


@user_bp.route('/settings/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        token = generate_token(user=current_user, operation=Operations.CHANGE_EMAIL, new_email=form.email.data)
        send_confirm_email(user=current_user, token=token)
        flash('Confirm email sent, check your inbox.', 'info')
        return redirect(url_for('user.index', username=current_user.username))
    return render_template('user/settings/change_email.html', form=form)

@user_bp.route('/change-email/<token>')
@login_required
def change_email(token):
    if validate_token(user=current_user, token=token, operation=Operations.CHANGE_EMAIL):
        flash('Email updated.', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    else:
        flash('Invalid or expired token.', 'warning')
        return redirect(url_for('user.change_email_request'))

@user_bp.route('/settings/notification', methods=['GET', 'POST'])
@login_required
def notification_setting():
    form = NotificationSettingForm()
    if form.validate_on_submit():
        current_user.receive_comment_notification = form.receive_comment_notification.data
        current_user.receive_follow_notification = form.receive_follow_notification.data
        current_user.receive_collect_notification = form.receive_collect_notification.data
        db.session.commit()
        flash('Notification settings updated.', 'success')
        return redirect(url_for('user.notification_setting'))
    form.receive_comment_notification.data = current_user.receive_comment_notification
    form.receive_follow_notification.data = current_user.receive_follow_notification
    form.receive_collect_notification.data = current_user.receive_collect_notification
    return render_template('user/settings/notification_setting.html', form=form)


@user_bp.route('/settings/privacy', methods=['GET', 'POST'])
@login_required
def privacy_setting():
    form = PrivacySettingForm()
    if form.validate_on_submit():
        current_user.public_collections = form.public_collections.data
        # current_user.receive_private_messages = form.receive_private_messages.data
        db.session.commit()
        flash('Privacy settings updated.', 'success')
        return redirect(url_for('user.privacy_setting'))
    form.public_collections.data = current_user.public_collections
    return render_template('user/settings/privacy_setting.html', form=form)


@user_bp.route('/settings/account/delete', methods=['GET', 'POST'])
@fresh_login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        # 使用current_user._get_current_object()获取真正的User对象 current_user是一个代理对象
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        flash('Account deleted.', 'success')
        return redirect(url_for('main.index'))
    return render_template('user/settings/delete_account.html', form=form)
