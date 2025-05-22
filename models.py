from app import db
from flask_login import UserMixin
from datetime import datetime
import os

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(256), default='')
    storage_limit = db.Column(db.BigInteger, default=1073741824)  # 1GB default storage
    storage_used = db.Column(db.BigInteger, default=0)
    security_question = db.Column(db.String(256))
    security_answer = db.Column(db.String(256))
    
    # Relationships
    files = db.relationship('File', backref='owner', lazy=True, cascade="all, delete-orphan")
    folders = db.relationship('Folder', backref='owner', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.username}>'

class StorageClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # photo, video, audio, document, etc.
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    folders = db.relationship('Folder', backref='storage_class', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<StorageClass {self.name} ({self.file_type})>'

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id', ondelete='CASCADE'), nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.BigInteger, default=0)  # Size in bytes
    storage_class_id = db.Column(db.Integer, db.ForeignKey('storage_class.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    files = db.relationship('File', backref='folder', lazy=True, cascade="all, delete-orphan")
    subfolders = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), lazy=True)
    
    def __repr__(self):
        return f'<Folder {self.name}>'
    
    def calculate_size(self):
        """Calculate total size of folder including all files and subfolders"""
        size = 0
        for file in self.files:
            size += file.size
        for subfolder in self.subfolders:
            size += subfolder.calculate_size()
        self.size = size
        return size

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # photo, video, audio, document, etc.
    mimetype = db.Column(db.String(128), nullable=False)
    size = db.Column(db.BigInteger, nullable=False)  # Size in bytes
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id', ondelete='CASCADE'), nullable=True)
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<File {self.filename}>'
    
    def get_path(self):
        """Get the full path to the file on disk"""
        from app import app
        return os.path.join(app.config['UPLOAD_FOLDER'], self.filename)
    
    def get_size_display(self):
        """Get a human-readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                break
            size /= 1024
        return f"{size:.2f} {unit}"
