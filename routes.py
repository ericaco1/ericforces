from flask import render_template, flash, redirect, url_for, request, send_file, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import os
import logging

from app import app, db
from models import User, File, Folder, StorageClass
from forms import (
    LoginForm, RegistrationForm, ProfilePictureForm, FolderForm, StorageClassForm,
    PasswordResetRequestForm, PasswordResetForm, AdminUserApprovalForm, AdminUserStorageForm,
    FileUploadForm
)
from utils import (
    save_file, delete_file, create_folder, delete_folder, get_human_readable_size, is_admin
)

# Index route
@app.route('/')
def index():
    return render_template('index.html', title='Welcome to EFORICE')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not check_password_hash(user.password_hash, form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        if not user.is_approved and not user.is_admin:
            return redirect(url_for('approval_pending'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard')
        
        flash('Login successful!', 'success')
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            security_question=form.security_question.data,
            security_answer=form.security_answer.data
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please wait for admin approval before logging in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

# Logout route
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    # Get storage usage
    storage_used = current_user.storage_used
    storage_limit = current_user.storage_limit
    storage_percent = (storage_used / storage_limit) * 100 if storage_limit > 0 else 0
    
    # Get file statistics
    total_files = File.query.filter_by(user_id=current_user.id).count()
    total_folders = Folder.query.filter_by(user_id=current_user.id).count()
    
    # Get recent files
    recent_files = File.query.filter_by(user_id=current_user.id).order_by(File.date_uploaded.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html', 
        title='Dashboard',
        storage_used=get_human_readable_size(storage_used),
        storage_limit=get_human_readable_size(storage_limit),
        storage_percent=storage_percent,
        total_files=total_files,
        total_folders=total_folders,
        recent_files=recent_files
    )

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfilePictureForm()
    if form.validate_on_submit():
        file = form.profile_picture.data
        if file:
            # Save profile picture
            filename = secure_filename(file.filename)
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                if ext.lower() in ['jpg', 'jpeg', 'png', 'gif']:
                    unique_filename = f"profile_{current_user.id}.{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    current_user.profile_picture = unique_filename
                    db.session.commit()
                    flash('Profile picture updated successfully!', 'success')
                else:
                    flash('Invalid file format. Please upload an image.', 'danger')
            else:
                flash('Invalid file format. Please upload an image.', 'danger')
    
    return render_template('profile.html', title='Profile', form=form)

# File Manager route
@app.route('/files')
@login_required
def file_manager():
    folder_id = request.args.get('folder_id', None, type=int)
    storage_class_id = request.args.get('storage_class_id', None, type=int)
    
    # Get current folder
    current_folder = None
    if folder_id:
        current_folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first_or_404()
    
    # Get storage class
    storage_class = None
    if storage_class_id:
        storage_class = StorageClass.query.filter_by(id=storage_class_id, user_id=current_user.id).first_or_404()
    
    # Get folders and files
    if current_folder:
        folders = Folder.query.filter_by(parent_id=current_folder.id, user_id=current_user.id).all()
        files = File.query.filter_by(folder_id=current_folder.id, user_id=current_user.id).all()
    elif storage_class:
        folders = Folder.query.filter_by(storage_class_id=storage_class.id, parent_id=None, user_id=current_user.id).all()
        files = File.query.filter_by(file_type=storage_class.file_type, folder_id=None, user_id=current_user.id).all()
    else:
        folders = Folder.query.filter_by(parent_id=None, storage_class_id=None, user_id=current_user.id).all()
        files = File.query.filter_by(folder_id=None, user_id=current_user.id).all()
    
    # Get storage classes
    storage_classes = StorageClass.query.filter_by(user_id=current_user.id).all()
    
    # Forms
    folder_form = FolderForm()
    storage_class_form = StorageClassForm()
    upload_form = FileUploadForm()
    
    return render_template(
        'file_manager.html',
        title='File Manager',
        current_folder=current_folder,
        storage_class=storage_class,
        folders=folders,
        files=files,
        storage_classes=storage_classes,
        folder_form=folder_form,
        storage_class_form=storage_class_form,
        upload_form=upload_form,
        get_human_readable_size=get_human_readable_size
    )

# Create folder route
@app.route('/folders/create', methods=['POST'])
@login_required
def create_folder_route():
    form = FolderForm()
    if form.validate_on_submit():
        parent_id = form.parent_id.data if form.parent_id.data else None
        storage_class_id = form.storage_class_id.data if form.storage_class_id.data else None
        
        folder, error = create_folder(form.name.data, current_user.id, parent_id, storage_class_id)
        if folder:
            flash(f'Folder "{form.name.data}" created successfully!', 'success')
        else:
            flash(f'Error creating folder: {error}', 'danger')
    
    return redirect(request.referrer or url_for('file_manager'))

# Delete folder route
@app.route('/folders/delete/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder_route(folder_id):
    success, error = delete_folder(folder_id, current_user.id)
    if success:
        flash('Folder deleted successfully!', 'success')
    else:
        flash(f'Error deleting folder: {error}', 'danger')
    
    return redirect(request.referrer or url_for('file_manager'))

# Create storage class route
@app.route('/storage-classes/create', methods=['POST'])
@login_required
def create_storage_class():
    form = StorageClassForm()
    if form.validate_on_submit():
        storage_class = StorageClass(
            name=form.name.data,
            file_type=form.file_type.data,
            user_id=current_user.id
        )
        db.session.add(storage_class)
        db.session.commit()
        flash(f'Storage class "{form.name.data}" created successfully!', 'success')
    
    return redirect(url_for('file_manager'))

# Delete storage class route
@app.route('/storage-classes/delete/<int:storage_class_id>', methods=['POST'])
@login_required
def delete_storage_class(storage_class_id):
    storage_class = StorageClass.query.filter_by(id=storage_class_id, user_id=current_user.id).first_or_404()
    
    # Delete all folders in this storage class
    folders = Folder.query.filter_by(storage_class_id=storage_class_id, user_id=current_user.id).all()
    for folder in folders:
        delete_folder(folder.id, current_user.id)
    
    db.session.delete(storage_class)
    db.session.commit()
    flash('Storage class deleted successfully!', 'success')
    
    return redirect(url_for('file_manager'))

# Upload file route
@app.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    form = FileUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        folder_id = form.folder_id.data if form.folder_id.data else None
        
        if file:
            new_file, error = save_file(file, current_user.id, folder_id)
            if new_file:
                flash('File uploaded successfully!', 'success')
            else:
                flash(f'Error uploading file: {error}', 'danger')
    
    return redirect(request.referrer or url_for('file_manager'))

# Download file route
@app.route('/files/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    
    if os.path.exists(filepath):
        return send_file(
            filepath,
            as_attachment=True,
            download_name=file.original_filename,
            mimetype=file.mimetype
        )
    
    flash('File not found!', 'danger')
    return redirect(request.referrer or url_for('file_manager'))

# Delete file route
@app.route('/files/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file_route(file_id):
    success, error = delete_file(file_id, current_user.id)
    if success:
        flash('File deleted successfully!', 'success')
    else:
        flash(f'Error deleting file: {error}', 'danger')
    
    return redirect(request.referrer or url_for('file_manager'))

# Search files route
@app.route('/search')
@login_required
def search_files():
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('file_manager'))
    
    # Search for files and folders
    files = File.query.filter(
        File.user_id == current_user.id,
        File.original_filename.ilike(f'%{query}%')
    ).all()
    
    folders = Folder.query.filter(
        Folder.user_id == current_user.id,
        Folder.name.ilike(f'%{query}%')
    ).all()
    
    return render_template(
        'file_manager.html',
        title=f'Search Results for "{query}"',
        files=files,
        folders=folders,
        search_query=query,
        get_human_readable_size=get_human_readable_size,
        folder_form=FolderForm(),
        upload_form=FileUploadForm()
    )

# Admin dashboard route
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get pending users
    pending_users = User.query.filter_by(is_approved=False).all()
    
    # Get all users
    all_users = User.query.filter(User.id != current_user.id).all()
    
    return render_template(
        'admin.html',
        title='Admin Dashboard',
        pending_users=pending_users,
        all_users=all_users,
        get_human_readable_size=get_human_readable_size
    )

# Admin approve user route
@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    flash(f'User {user.username} has been approved!', 'success')
    return redirect(url_for('admin_dashboard'))

# Admin reject user route
@app.route('/admin/reject/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.username} has been rejected!', 'success')
    return redirect(url_for('admin_dashboard'))

# Admin update user storage route
@app.route('/admin/update-storage/<int:user_id>', methods=['POST'])
@login_required
def update_user_storage(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    storage_limit = request.form.get('storage_limit', type=float)
    if not storage_limit or storage_limit <= 0:
        flash('Invalid storage limit!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.storage_limit = int(storage_limit * 1024 * 1024 * 1024)  # Convert GB to bytes
    db.session.commit()
    
    flash(f'Storage limit for {user.username} updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Password reset request route
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('If your email is registered, you will be redirected to the security question page.', 'info')
            return redirect(url_for('reset_password', user_id=user.id))
        else:
            flash('If your email is registered, you will be redirected to the security question page.', 'info')
    
    return render_template('reset_password_request.html', title='Reset Password', form=form)

# Password reset route
@app.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = PasswordResetForm()
    
    if request.method == 'GET':
        form.username.data = user.username
    
    if form.validate_on_submit():
        if form.username.data != user.username:
            flash('Invalid username!', 'danger')
            return redirect(url_for('reset_password', user_id=user_id))
        
        if form.security_answer.data != user.security_answer:
            flash('Invalid security answer!', 'danger')
            return redirect(url_for('reset_password', user_id=user_id))
        
        user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        
        flash('Your password has been reset successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template(
        'reset_password.html',
        title='Reset Password',
        form=form,
        security_question=user.security_question
    )

# Approval pending route
@app.route('/approval-pending')
def approval_pending():
    return render_template('approval_pending.html', title='Approval Pending')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', title='Page Not Found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html', title='Server Error'), 500

# API routes for sorting and filtering
@app.route('/api/files/sort')
@login_required
def api_sort_files():
    folder_id = request.args.get('folder_id', None, type=int)
    sort_by = request.args.get('sort_by', 'date_uploaded')
    order = request.args.get('order', 'desc')
    
    # Build query
    query = File.query.filter_by(user_id=current_user.id)
    if folder_id is not None:
        query = query.filter_by(folder_id=folder_id)
    
    # Apply sorting
    if sort_by == 'name':
        query = query.order_by(File.original_filename.asc() if order == 'asc' else File.original_filename.desc())
    elif sort_by == 'date':
        query = query.order_by(File.date_uploaded.asc() if order == 'asc' else File.date_uploaded.desc())
    elif sort_by == 'size':
        query = query.order_by(File.size.asc() if order == 'asc' else File.size.desc())
    elif sort_by == 'type':
        query = query.order_by(File.file_type.asc() if order == 'asc' else File.file_type.desc())
    
    files = query.all()
    
    # Prepare data for response
    result = []
    for file in files:
        result.append({
            'id': file.id,
            'name': file.original_filename,
            'type': file.file_type,
            'size': get_human_readable_size(file.size),
            'date': file.date_uploaded.strftime('%Y-%m-%d %H:%M:%S'),
            'download_url': url_for('download_file', file_id=file.id)
        })
    
    return jsonify(result)
