# -*- coding: utf-8 -*-
import os

from flask import render_template, Blueprint, request, current_app, send_from_directory, redirect, flash, url_for, \
    abort, jsonify
from flask_dropzone import random_filename
from flask_login import login_required, current_user
from sqlalchemy import func

from albumy.extensions import db
from albumy.decorators import confirm_required, permission_required
from albumy.forms.main import DescriptionForm, TagForm, CommentForm
from albumy.models import Photo, Tag, Comment, Notification, Follow, Collect, User
from albumy.nitifications import push_collect_notification, push_comment_notification
from albumy.utils import flash_errors, redirect_back, resize_image

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # filter和filter_by的区别:filter_by只能用于等值判断，filter可以用于其他判断
        followed_photos = Photo.query. \
            join(Follow, Follow.followed_id == Photo.author_id). \
            filter(Follow.follower_id == current_user.id). \
            order_by(Photo.timestamp.desc())
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
        pagination = followed_photos.paginate(page=page, per_page=per_page)
        photos = pagination.items
    else:
        pagination = None
        photos = None
    tags = Tag.query. \
        join(Tag.photos). \
        group_by(Tag.id). \
        order_by(func.count(Photo.id).desc()). \
        limit(10)
    return render_template('main/index.html', pagination=pagination, photos=photos, tags=tags, Collect=Collect)


@main_bp.route('/explore')
def explore():
    photos = Photo.query.order_by(func.random()).limit(12)
    return render_template('main/explore.html', photos=photos)


@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@confirm_required
@permission_required('UPLOAD')
def upload():
    if request.method == 'POST' and 'file' in request.files:
        # 可以使用一个函数来检查上传的图片是否合法
        # if not check_image(f):
        #     return 'Invalid image.', 400
        f = request.files.get('file')
        filename = random_filename(f.filename)
        f.save(os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename))
        filename_s = resize_image(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['small'])
        filename_m = resize_image(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['medium'])
        photo = Photo(filename=filename,
                      filename_s=filename_s,
                      filename_m=filename_m,
                      author=current_user._get_current_object(),
                      )
        db.session.add(photo)
        db.session.commit()
    return render_template('main/upload.html')


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


@main_bp.route('/uplodas/<path:filename>')
def get_image(filename):
    return send_from_directory(current_app.config['ALBUMY_UPLOAD_PATH'], filename)


@main_bp.route('/photo/<int:photo_id>')
def show_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_COMMENT_PER_PAGE']
    pagination = Comment.query.with_parent(photo).order_by(Comment.timestamp.asc()).paginate(page=page, per_page=per_page)
    comments = pagination.items
    
    comment_form = CommentForm()
    description_form = DescriptionForm()
    tag_form = TagForm()
    
    description_form.description.data = photo.description
    return render_template('main/photo.html', photo=photo, comment_form=comment_form,
                           description_form=description_form, tag_form=tag_form,
                           pagination=pagination, comments=comments)


@main_bp.route('/photo/n/<int:photo_id>')
def photo_next(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    # with_parent() 方法可以指定查询的父模型，这样就可以避免使用 filter_by() 方法
    photo_n = Photo.query.with_parent(photo.author).filter(Photo.id > photo.id).order_by(Photo.id.asc()).first()
    if photo_n is None:
        flash('This is the last photo.', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo_id))
    return redirect(url_for('main.show_photo', photo_id=photo_n.id))


@main_bp.route('/photo/p/<int:photo_id>')
def photo_previous(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    # with_parent() 方法可以指定查询的父模型，这样就可以避免使用 filter_by() 方法 这里filter()是过滤器
    photo_p = Photo.query.with_parent(photo.author).filter(Photo.id < photo.id).order_by(Photo.id.desc()).first()
    if photo_p is None:
        flash('This is the last photo.', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo_id))
    return redirect(url_for('main.show_photo', photo_id=photo_p.id))


@main_bp.route('/photo/<int:photo_id>/description', methods=['POST'])
@login_required
def edit_description(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    
    form = DescriptionForm()
    if form.validate_on_submit():
        photo.description = form.description.data
        db.session.commit()
        flash('Description updated.', 'success')
    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/photo/set-comment/<int:photo_id>', methods=['POST'])
@login_required
def set_comment(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    
    if photo.can_comment:
        photo.can_comment = False
        flash('Comment disabled.', 'info')
    else:
        photo.can_comment = True
        flash('Comment enabled.', 'info')
    db.session.commit()
    return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/report/photo/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
def report_photo(photo_id):
    photo = Photo.query.git_or_404(photo_id)
    photo.flag += 1
    db.session.commit()
    flash('Photo reported.', 'success')
    return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/collect/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
@permission_required('COLLECT')
def collect(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        flash('Already collected.', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo_id))
    current_user.collect(photo)
    flash('Photo collected.', 'success')
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(collector=current_user, photo_id=photo_id, recipient=photo.author)
    return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
@login_required
def uncollect(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        current_user.uncollect(photo)
        flash('Photo uncollected.', 'success')
        return redirect(url_for('main.show_photo', photo_id=photo_id))
    flash('Not collect yet.', 'info')
    return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/photo/<int:photo_id>/collectors')
def show_collectors(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_PHOTO_COLLECTORS_PER_PAGE']
    pagination = photo.collectors.paginate(page=page, per_page=per_page)
    collects = pagination.items
    return render_template('main/collectors.html', photo=photo, pagination=pagination, collects=collects)


@main_bp.route('/delete/photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.', 'success')
    
    photo_to_show = Photo.query.with_parent(photo.author).filter(Photo.id > photo.id).order_by(Photo.id.asc()).first()
    if photo_to_show is None:
        photo_to_show = Photo.query.with_parent(photo.author).filter(Photo.id < photo.id).order_by(
            Photo.id.desc()).first()
    if photo_to_show is None:
        return redirect(url_for('user.index', username=photo.author.username))
    return redirect(url_for('main.show_photo', photo_id=photo_to_show.id))


@main_bp.route('/photo/<int:photo_id>/tag/new', methods=['POST'])
@login_required
def new_tag(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    
    form = TagForm()
    if form.validate_on_submit():
        for name in form.tag.data.split():
            tag = Tag.query.filter_by(name=name).first()
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
            if tag not in photo.tags:
                photo.tags.append(tag)
        db.session.commit()
        flash('Tag added.', 'success')
        return redirect(url_for('main.show_photo', photo_id=photo_id))


@main_bp.route('/tag/<int:tag_id>', defaults={'order': 'by_time'})
@main_bp.route('/tag/<int:tag_id>/<order>')
def show_tag(tag_id, order):
    tag = Tag.query.get_or_404(tag_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
    if order == 'by_time':
        order_rule = 'time'
        pagination = Photo.query.with_parent(tag).order_by(Photo.timestamp.desc()).paginate(page=page, per_page=per_page)
    if order == 'by_collects':
        order_rule = 'collects'
        pagination = Photo.query.with_parent(tag).order_by(Photo.collectors_count.desc()).paginate(page=page, per_page=per_page)
    photos = pagination.items
    
    return render_template('main/tag.html', tag=tag, photos=photos, pagination=pagination, order_rule=order_rule)


@main_bp.route('/delete/tag/<int:photo_id>/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(photo_id, tag_id):
    tag = Tag.query.get_or_404(tag_id)
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    photo.tags.remove(tag)
    if not tag.photos:
        db.session.delete(tag)
    
    db.session.commit()
    flash('Tag deleted.', 'success')
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/photo/<int:photo_id>/comment/new', methods=['POST'])
@login_required
def new_comment(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    if form.validate_on_submit():
        body = form.body.data
        author = current_user._get_current_object()
        comment = Comment(body=body, photo=photo, author=author)
        replied_id = request.args.get('reply')
        if replied_id:
            print(Comment.query.get_or_404(replied_id))
            comment.replied = Comment.query.get_or_404(replied_id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment published.', 'success')
        if current_user != photo.author and photo.author.receive_comment_notification:
            push_comment_notification(photo_id=photo_id, receiver=photo.author)
    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo_id, page=page))


@main_bp.route('/reply/comment/<int:comment_id>')
@login_required
@permission_required('COMMENT')
def reply_comment(comment_id):
    # 直接定位到评论框
    comment = Comment.query.get_or_404(comment_id)
    return redirect(
        url_for('main.show_photo', photo_id=comment.photo_id, reply=comment_id, author=comment.author.name)
        + '#comment-form')


@main_bp.route('/report/comment/<int:comment_id>', methods=['POST'])
@login_required
@confirm_required
def report_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.flag += 1
    db.session.commit()
    flash('Comment reported.', 'success')
    return redirect(url_for('main.show_photo', photo_id=comment.photo_id))


@main_bp.route('/delete/comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user != comment.author and not current_user.can('MODERATE'):
        abort(403)
    
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted.', 'success')
    return redirect(url_for('main.show_photo', photo_id=comment.photo_id))


@main_bp.route('/notifications')
@login_required
def show_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_NOTIFICATION_PER_PAGE']
    notifications = Notification.query.with_parent(current_user)
    filter_rule = request.args.get('filter')
    if filter_rule == 'unread':
        notifications = notifications.filter_by(is_read=False)
    pagination = notifications.order_by(Notification.timestamp.desc()).paginate(page=page, per_page=per_page)
    notifications = pagination.items
    return render_template('main/notifications.html', notifications=notifications, pagination=pagination)


@main_bp.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if current_user != notification.receiver:
        abort(403)
    notification.is_read = True
    db.session.commit()
    flash('Notification archived.', 'success')
    return redirect(url_for('main.show_notifications'))


@main_bp.route('/notifications/read/all', methods=['POST'])
@login_required
def read_all_notification():
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    flash('All notifications archived.', 'success')
    return redirect(url_for('main.show_notifications'))


@main_bp.route('/search')
def search():
    q = request.args.get('q', '')
    if q == '':
        flash('Please enter keywords.', 'warning')
        return redirect_back()
    category = request.args.get('category', 'photo')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_SEARCH_RESULT_PER_PAGE']
    if category == 'user':
        pagination = User.query.whooshee_search(q).paginate(page=page, per_page=per_page)
    if category == 'photo':
        pagination = Photo.query.whooshee_search(q).paginate(page=page, per_page=per_page)
    if category == 'tag':
        pagination = Tag.query.whooshee_search(q).paginate(page=page, per_page=per_page)
    results = pagination.items
    return render_template('main/search.html', q=q, category=category, pagination=pagination, results=results)
