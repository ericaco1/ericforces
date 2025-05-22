import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename
from flask import current_app
from models import File, User, Folder
from app import db
import logging

# File type mapping
FILE_TYPES = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'tiff'],
    'video': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', '3gp'],
    'audio': ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma'],
    'document': ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'csv', 'odt', 'rtf'],
    'other': []
}

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    for file_type, extensions in FILE_TYPES.items():
        if ext in extensions:
            return file_type
    
    return 'other'

def get_unique_filename(original_filename):
    """Generate a unique filename to prevent overwriting"""
    filename = secure_filename(original_filename)
    unique_id = str(uuid.uuid4())
    # Get the file extension
    if '.' in filename:
        name, ext = filename.rsplit('.', 1)
        return f"{name}_{unique_id}.{ext}"
    return f"{filename}_{unique_id}"

def save_file(file, user_id, folder_id=None):
    """Save uploaded file to disk and database"""
    try:
        # Get the file details
        original_filename = file.filename
        mimetype = file.content_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        file_type = get_file_type(original_filename)
        
        # Generate a unique filename
        unique_filename = get_unique_filename(original_filename)
        
        # Get the file path
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save the file to disk
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Update user's storage usage
        user = User.query.get(user_id)
        if user.storage_used + file_size > user.storage_limit:
            # Remove the file if it exceeds the user's storage limit
            os.remove(filepath)
            return None, "File exceeds your storage limit"
        
        user.storage_used += file_size
        
        # Create a new file record
        new_file = File(
            filename=unique_filename,
            original_filename=original_filename,
            file_type=file_type,
            mimetype=mimetype,
            size=file_size,
            user_id=user_id,
            folder_id=folder_id
        )
        
        # Update folder size if file is in a folder
        if folder_id:
            folder = Folder.query.get(folder_id)
            if folder:
                folder.size += file_size
                # Update parent folder sizes recursively
                parent = folder.parent
                while parent:
                    parent.size += file_size
                    parent = parent.parent
        
        db.session.add(new_file)
        db.session.commit()
        
        return new_file, None
    except Exception as e:
        logging.error(f"Error saving file: {str(e)}")
        return None, str(e)

def delete_file(file_id, user_id):
    """Delete a file from disk and database"""
    try:
        file = File.query.filter_by(id=file_id, user_id=user_id).first()
        if not file:
            return False, "File not found"
        
        # Get the file path
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        
        # Delete the file from disk
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Update user's storage usage
        user = User.query.get(user_id)
        user.storage_used -= file.size
        
        # Update folder size if file is in a folder
        if file.folder_id:
            folder = Folder.query.get(file.folder_id)
            if folder:
                folder.size -= file.size
                # Update parent folder sizes recursively
                parent = folder.parent
                while parent:
                    parent.size -= file.size
                    parent = parent.parent
        
        # Delete the file record
        db.session.delete(file)
        db.session.commit()
        
        return True, None
    except Exception as e:
        logging.error(f"Error deleting file: {str(e)}")
        return False, str(e)

def create_folder(name, user_id, parent_id=None, storage_class_id=None):
    """Create a new folder"""
    try:
        folder = Folder(
            name=name,
            user_id=user_id,
            parent_id=parent_id,
            storage_class_id=storage_class_id
        )
        db.session.add(folder)
        db.session.commit()
        return folder, None
    except Exception as e:
        logging.error(f"Error creating folder: {str(e)}")
        return None, str(e)

def delete_folder(folder_id, user_id):
    """Delete a folder and all its contents"""
    try:
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return False, "Folder not found"
        
        # Get the size of the folder
        folder_size = folder.size
        
        # Delete all files in the folder
        for file in folder.files:
            delete_file(file.id, user_id)
        
        # Delete all subfolders recursively
        for subfolder in folder.subfolders:
            delete_folder(subfolder.id, user_id)
        
        # Update parent folder size
        if folder.parent_id:
            parent = Folder.query.get(folder.parent_id)
            if parent:
                parent.size -= folder_size
                # Update parent folder sizes recursively
                grandparent = parent.parent
                while grandparent:
                    grandparent.size -= folder_size
                    grandparent = grandparent.parent
        
        # Delete the folder record
        db.session.delete(folder)
        db.session.commit()
        
        return True, None
    except Exception as e:
        logging.error(f"Error deleting folder: {str(e)}")
        return False, str(e)

def get_human_readable_size(size_bytes):
    """Convert bytes to human-readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def is_admin(user):
    """Check if user is an admin"""
    return user.is_admin if user else False
