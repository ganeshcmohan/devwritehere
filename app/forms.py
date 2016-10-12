from wtforms.fields import HiddenField, TextField, TextAreaField, PasswordField, BooleanField, SelectMultipleField
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms.validators import Required, Optional, Email, Length, Regexp, ValidationError, EqualTo
from flask.ext.uploads import UploadSet
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from . import models as m
from .models import User, SQLMailBox
from .settings import TOPIC_NEW_DATE

class UniqueUser(object):
    def __init__(self, message="User exists"):
        self.message = message

    def __call__(self, form, field):
        user = User.objects(email=field.data).first()
        if user:
            raise ValidationError(self.message)

class UniqueEmail(object):
    def __init__(self, message="Email exists already."):
        self.message = message

    def __call__(self, form, field):
        email = SQLMailBox.query.filter_by(username=field.data).first()
        if email:
            raise ValidationError(self.message)

images = UploadSet("images", ('JPG', 'JPEG', 'GIF', 'PNG', 'SVG', 'jpg', 'jpeg', 'gif', 'png', 'svg'))

validators = {
    'headline': [
        Required()
    ],
    'content': [
        Required()
    ],
    'topics': [
        Required()
    ],
    'email': [
        Required(),
        Email(),
        UniqueUser(message='Email address is associated with an existing account')
        #UniqueUser(message='email exists')
    ],
    'new_email': [
        Required(),
        Email(),
        UniqueUser(message='Email address is associated with an existing account')
    ],
    'forgot_email': [
        Required(),
        Email(),
    ],
    'password': [
        Required(),
        Length(min=6, max=50),
        EqualTo('confirm', message='passwords must match'),
        Regexp(r'[A-Za-z0-9@#$%^&+=]',
            message='password contains invalid characters')
    ],
    'admin_password': [
        EqualTo('confirm', message='passwords must match'),
    ],
    'name': [
        Required(),
        Length(min=2, max=100)
    ],
    'photo': [
        Optional(),
        FileAllowed(images, 'Please only use JPG, PNG, or GIF images!')
    ],
    'display_name': [
        Required(),
        Length(min=3, max=100)
    ],
    'extract': [
        Optional(),
        Length(max=200)
    ],
    'delete_photo': [
        Optional()
    ],
    'terms': [
        Optional()
    ],
    'email_alias': [
        Required(),
        Regexp(r'[A-Za-z0-9]', message='Email must contain letters or numbers only.')
    ],
}

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

def load_topics():
    return [(str(t.id), t.topic) for t in m.Topic.objects(date_created__lte=TOPIC_NEW_DATE)]

class PostForm(Form):
    headline = TextField('Headline', validators['headline'])
    content = TextAreaField('Body', validators['content'])
    topics = SelectMultipleField('Topics', choices=[])
    photo = FileField('Photo', validators['photo'])
    extract = TextAreaField('Extract', validators['extract'])
    delete_photo = HiddenField('Delete Photo', validators['delete_photo'])
    photo_source = TextField('Photo Source')
    twitter_post = BooleanField("Tweet a link to my opinion via my Twitter account.", default=True)
    facebook_post = BooleanField("Post a link to my opinion on my Facebook Wall.", default=True)
    linkedin_post = BooleanField("Post a link to my opinion to my LinkedIn Share.", default=True)
    save_draft = HiddenField("Save this opinion as a draft.", default=False)
    #linkedin_post = BooleanField("Update my LinkedIn profile to link to my opinion.", default=True)

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args,**kwargs);
        self.topics.choices = load_topics()

class RegisterForm(Form):
    email = TextField('Email', validators['email'])
    display_name = TextField('Display Name', validators['display_name'])
    password = PasswordField('Password', validators['password'], )
    confirm = PasswordField('Confirm Password')
    # remember = BooleanField("Remember Me?", default=True)
    terms = BooleanField("I agree to the terms")

class ProfileForm(Form):
    display_name = TextField('display name:', validators['display_name'])
    location = TextField('at home in:')
    web_presence = TextAreaField('find my writing online at:')
    bio =  TextAreaField('bio:')
    photo = FileField('photo', validators['photo'])

class CommentForm(Form):
    extract = HiddenField()
    comment = TextAreaField()

class ReplyForm(Form):
    reply = TextAreaField()

class UploadForm(Form):
    photo = FileField('Photo', validators['photo'])

class ForgotPasswordForm(Form):
    email = TextField('Email', validators['forgot_email'])

class ResetPasswordForm(Form):
    password = PasswordField('new password:', validators['password'])
    confirm = PasswordField('confirm:')
    reset_code = HiddenField()

class ChangeEmailForm(Form):
    email = TextField('your email (not displayed on your profile page):', validators['email'])

class CropForm(Form):
    center_x = HiddenField()
    center_y = HiddenField()
    prop_x = HiddenField()
    prop_y = HiddenField()
    zoom = HiddenField()
    orientation = HiddenField()

""" Admin Forms """

class AdminUserForm(Form):

    # profile table
    display_name = TextField('Display Name', validators['display_name'])
    location = TextField('Location')
    web_presence = TextAreaField('Web Presence')
    bio =  TextAreaField('Bio')

    # user table
    email = TextField('Email', validators['email'])
    verified = BooleanField('Email verified')
    password = PasswordField('Password', validators['admin_password'])
    confirm = PasswordField('Confirm')

class AdminPostForm(Form):
    headline = TextField('Headline', validators['headline'])
    content = TextAreaField('Body', validators['content'])
    #topics = TextField('Topics', validators['topics'])
    topics = MultiCheckboxField('Topics', choices=[])
    extract = TextAreaField('Extract', validators['extract'])
    is_spam = BooleanField('Is Spam', [Optional()])

    def __init__(self, *args, **kwargs):
        super(AdminPostForm, self).__init__(*args,**kwargs);
        self.topics.choices = load_topics()

class AdminTopicForm(Form):
    topic = TextField('Topic', [Required()])
    as_new = BooleanField('Use as new', [Optional()])

class AdminEmailForm(Form):
    name = TextField('Full Name', [Required()])
    password = PasswordField('Password', validators['admin_password'])
    confirm = PasswordField('Confirm')

class AdminEmailCreateForm(AdminEmailForm):
    alias = TextField('Email Account', validators['email_alias'])

class AdminPage(Form):
    title = TextField('Page Title')
    content = TextAreaField('Page Content')
    slug = HiddenField()
