from flask import Blueprint, abort, make_response, render_template, request, redirect, url_for, jsonify, flash
from flask.ext.login import login_required, current_user
from bson.objectid import ObjectId
import datetime
from ..models import Post, User, Profile
from ..forms import CropForm, UploadForm
from ..util import hashed, get_user_object, nocache

media = Blueprint('media', __name__, template_folder='../templates')

@media.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    user = get_user_object(current_user)
    form = UploadForm()

    if form.validate_on_submit():
        photo = request.files['photo']
        if photo:
            if user.crop_photo:
                user.crop_photo.replace(photo, content_type=photo.mimetype)
            else:
                user.crop_photo.put(photo, content_type=photo.mimetype)

        user.save()

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Please upload image files only'})


@media.route('/upload-avatar', methods=['GET','POST'])
@login_required
def upload_avatar():
    user = get_user_object(current_user)
    form = UploadForm()

    if form.validate_on_submit():
        photo = request.files['photo']
        if photo:
            if user.avatar_full:
                user.avatar_full.replace(photo, content_type=photo.mimetype)
            else:
                user.avatar_full.put(photo, content_type=photo.mimetype)

        user.save()

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Please upload image files only'})

@media.route('/show-avatar/<user_id>')
@media.route('/show-avatar/<user_id>/<size>')
def show_avatar(user_id, size='small'):
    try:
        user = User.objects(id=ObjectId(user_id)).only('avatar', 'avatar_full').first()
        if size == 'small':
            file = user.avatar
        else:
            file = user.avatar_full
        response = make_response(file.read())
        response.mimetype = file.content_type

        response.headers.add('Last-Modified', datetime.datetime.now())
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        response.headers.add('Pragma', 'no-cache')

        return response
    except:
        response = make_response('data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==')
        response.mimetype = 'image/gif'
        return response

@media.route('/remove', methods=['POST'])
@login_required
def remove():
    user = get_user_object(current_user)
    user.crop_photo.delete()
    user.crop_photo = None
    user.save()
    return jsonify({'success': True, 'message': 'Removed pending photo upload'})

@media.route('/crop-photo')
@nocache
@login_required
def crop_photo_url():
    user = get_user_object(current_user)
    try:
        file = user.crop_photo
        response = make_response(file.read())
        response.mimetype = file.content_type

        response.headers.add('Last-Modified', datetime.datetime.now())
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        response.headers.add('Pragma', 'no-cache')

        return response
    except:
        response = make_response('data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==')
        response.mimetype = 'image/gif'
        return response

@media.route('/crop-avatar', methods=['GET','POST'])
@login_required
def crop_avatar():
    from PIL import Image
    import StringIO
    crop_form = CropForm()

    user = get_user_object(current_user)


    if crop_form.validate_on_submit():
        file = user.avatar_full
        crop_io = StringIO.StringIO()

        crop_w = 300
        crop_h = 300

        center_x = float(crop_form.center_x.data)
        center_y = float(crop_form.center_y.data)
        zoom = float(crop_form.zoom.data)

        new_w = (crop_w / zoom)
        new_h = (crop_h / zoom)

        img_orig = Image.open(file)
        img_orig = img_orig.convert("RGBA")
        img = Image.new("RGB", img_orig.size, (255,255,255))
        img.paste(img_orig,img_orig)

        left = center_x - (new_w / 2)
        top = center_y - (new_h / 2)
        right = left + new_w
        bottom = top + new_h

        box = (int(left), int(top), int(right), int(bottom))

        cropped =  img.crop(box)
        cropped.thumbnail((crop_w, crop_h), Image.ANTIALIAS)
        cropped.save(crop_io, 'JPEG')

        if user.avatar:
            user.avatar.replace(crop_io.getvalue(), content_type='JPEG')
        else:
            user.avatar.put(crop_io.getvalue(), content_type='JPEG')
        user.save()

        return jsonify({'success': True})


    return jsonify({'success': False, 'message': 'Failed to crop image'})

@media.route('/crop', methods=['GET','POST'])
@login_required
def crop():
    from PIL import Image
    import StringIO
    crop_form = CropForm()

    user = get_user_object(current_user)


    if crop_form.validate_on_submit():
        file = user.crop_photo
        crop_io = StringIO.StringIO()

        center_x = float(crop_form.center_x.data)
        center_y = float(crop_form.center_y.data)
        zoom = float(crop_form.zoom.data)

        orientation = crop_form.orientation.data

        if orientation == 'vertical':
            crop_w = 300
            crop_h = 400
        else:
            crop_w = 400
            crop_h = 300

        new_w = (crop_w / zoom)
        new_h = (crop_h / zoom)

        img_orig = Image.open(file)
        img_orig = img_orig.convert("RGBA")
        img = Image.new("RGB", img_orig.size, (255,255,255))
        img.paste(img_orig, img_orig)

        left = center_x - (new_w / 2)
        top = center_y - (new_h / 2)
        right = left + new_w
        bottom = top + new_h

        box = (int(left), int(top), int(right), int(bottom))

        cropped =  img.crop(box)
        cropped.thumbnail((crop_w, crop_h), Image.ANTIALIAS)
        cropped.save(crop_io, 'JPEG')

        if user.crop_photo:
            user.crop_photo.replace(crop_io.getvalue(), content_type='JPEG')
        else:
            user.crop_photo.put(crop_io.getvalue(), content_type='JPEG')
        user.crop_photo_orientation = orientation
        user.save()

        return jsonify({'success': True})


    return jsonify({'success': False, 'message': 'Failed to crop image'})

@media.route('/photos/user/<user_id>')
def user_photo(user_id):
    try:
        user = User.objects(id=ObjectId(user_id)).only('id').first()
        profile = Profile.objects(user=user).only('photo').first()
        file = profile.photo
        #return send_file(file, mimetype=file.content_type)
        response = make_response(file.read())
        response.mimetype = file.content_type

        response.headers.add('Last-Modified', datetime.datetime.now())
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        response.headers.add('Pragma', 'no-cache')

        return response
    except:
        abort(404)


@media.route('/photos/opinion/<post_id>')
def post_photo(post_id, width=200):
    try:
        post = Post.objects(id=ObjectId(post_id)).only('photo').first()
        file = post.photo
        #return send_file(file, mimetype=file.content_type)
        response = make_response(file.read())
        response.mimetype = file.content_type

        response.headers.add('Last-Modified', datetime.datetime.now())
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        response.headers.add('Pragma', 'no-cache')

        return response
    except:
        abort(404)

@media.route('/photos/user/remove/<user_id>')
@login_required
def remove_user_photo(user_id):
    try:
        user = User.objects(id=ObjectId(user_id)).first()
        if user.id != current_user.id: return abort(403)
        user.avatar.delete()
        user.avatar_full.delete()
        user.save()
        return redirect(request.referrer or url_for('account.profile'))
    except:
        flash('Failed to delete photo', 'error')
        return redirect(request.referrer or url_for('account.profile'))