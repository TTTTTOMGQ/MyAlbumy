# -*- coding: utf-8 -*-
import os

from flask import render_template, Blueprint, request, current_app, send_from_directory, redirect, flash, url_for, abort
from flask_dropzone import random_filename
from flask_login import login_required, current_user

from albumy.extensions import db
from albumy.decorators import confirm_required, permission_required
from albumy.forms.main import DescriptionForm, TagForm, CommentForm
from albumy.models import Photo, Tag, Comment
from albumy.utils import flash_errors

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('main/index.html')


@main_bp.route('/explore')
def explore():
    return render_template('main/explore.html')


@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@confirm_required
@permission_required('UPLOAD')
def upload():
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')
        # 可以使用一个函数来检查上传的图片是否合法
        # if not check_image(f):
        #     return 'Invalid image.', 400
        filename = random_filename(f.filename)
        f.save(os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename))
        filename_s = Photo.resize(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['small'])
        filename_m = Photo.resize(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['medium'])
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
    return send_from_directory(current_app.config['AVATARS_UPLOAD_PATH'], filename)


@main_bp.route('/photo/<int:photo_id>')
def show_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    description_form = DescriptionForm()
    description_form.description.data = photo.description
    return render_template('main/photo.html', photo=photo, description_form=description_form)


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
        pagination = Photo.query.with_parent(tag).order_by(Photo.timestamp.desc()).paginate(page, per_page)
    if order == 'by_collects':
        order_rule = 'collects'
        pagination = Photo.query.with_parent(tag).order_by(Photo.collectors_count.desc()).paginate(page, per_page)
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
            comment.replied = Comment.query.get_or_404(replied_id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment published.', 'success')
    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo_id, page=page))


@main_bp.route('/reply/comment/<int:comment_id>', methods=['POST'])
@login_required
@permission_required('COMMENTS')
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
