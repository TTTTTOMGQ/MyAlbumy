# -*- codeing = utf-8 -*-
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from albumy.decorators import confirm_required, permission_required
from albumy.models import User
from albumy.nitifications import push_follow_notification

ajax_bp = Blueprint('ajax', __name__)


@ajax_bp.route('/profile/<int:user_id>')
def get_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('main/profile_popup.html', user=user)


@ajax_bp.route('/follow/<username>', methods=['POST'])
def follow(username):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403
    if not current_user.confirmed:
        return jsonify(message='Please confirm your account.'), 400
    if not current_user.can('FOLLOW'):
        return jsonify(message='Insufficient permissions.'), 403
    
    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_following(user):
        return jsonify(message='Already followed.'), 400
    current_user.follow(user)
    if user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return jsonify(message='User followed.'), 200


@ajax_bp.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403
    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_following(user):
        return jsonify(message='Not followed yet.'), 400
    current_user.unfollow(user)
    return jsonify(message='User unfollowed.'), 200


@ajax_bp.route('/followers-count/<int:user_id>')
def followers_count(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(count=user.followers.count() - 1), 200


@ajax_bp.route('/notifications-count')
def notifications_count():
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403
    count = current_user.notifications.filter_by(is_read=False).count()
    return jsonify(count=count), 200
