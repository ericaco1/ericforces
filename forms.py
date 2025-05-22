from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    security_question = StringField('Security Question', validators=[DataRequired()])
    security_answer = StringField('Security Answer', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProfilePictureForm(FlaskForm):
    profile_picture = FileField('Profile Picture', validators=[DataRequired()])
    submit = SubmitField('Upload')

class FolderForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(max=128)])
    parent_id = HiddenField('Parent Folder ID')
    storage_class_id = HiddenField('Storage Class ID')
    submit = SubmitField('Create Folder')

class StorageClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=64)])
    file_type = SelectField('File Type', choices=[
        ('photo', 'Photos'), 
        ('video', 'Videos'), 
        ('audio', 'Audio'), 
        ('document', 'Documents'),
        ('other', 'Other')
    ])
    submit = SubmitField('Create Class')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class PasswordResetForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    security_answer = StringField('Security Answer', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class AdminUserApprovalForm(FlaskForm):
    user_id = HiddenField('User ID', validators=[DataRequired()])
    approve = SubmitField('Approve')
    reject = SubmitField('Reject')

class AdminUserStorageForm(FlaskForm):
    user_id = HiddenField('User ID', validators=[DataRequired()])
    storage_limit = StringField('Storage Limit (GB)', validators=[DataRequired()])
    submit = SubmitField('Update Storage Limit')

class FileUploadForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    folder_id = HiddenField('Folder ID')
    submit = SubmitField('Upload')
