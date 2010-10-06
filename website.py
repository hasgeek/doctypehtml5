#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Website server for doctypehtml5.in
"""

from __future__ import with_statement
from datetime import datetime
from uuid import uuid4
from base64 import b64encode
from flask import Flask, abort, request, render_template, redirect, url_for
from flask import flash, session, g
from werkzeug import generate_password_hash, check_password_hash
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.mail import Mail, Message
from flaskext.wtf import Form, TextField, TextAreaField, PasswordField
from flaskext.wtf import Required, Email, ValidationError
from pytz import utc, timezone
from markdown import markdown
try:
    from greatape import MailChimp, MailChimpError
except ImportError:
    MailChimp = None

app = Flask(__name__)
db = SQLAlchemy(app)
mail = Mail(app)

# ---------------------------------------------------------------------------
# Static data

USER_CATEGORIES = [
    (0, u'Unclassified'),
    (1, u'Student or Trainee'),
    (2, u'Developer'),
    (3, u'Designer'),
    (4, u'Manager, Senior Developer/Designer'),
    (5, u'CTO, CIO, CEO'),
    (6, u'Entrepreneur'),
    ]

TSHIRT_SIZES = [
    (0, u'Unknown'),
    (1, u'XS'),
    (2, u'S'),
    (3, u'M'),
    (4, u'L'),
    (5, u'XL'),
    (6, u'XXL'),
    (7, u'XXXL'),
    ]

REFERRERS = [
    (0, u'Unspecified'),
    (1, u'Twitter'),
    (2, u'Facebook'),
    (3, u'LinkedIn'),
    (4, u'Google/Bing Search'),
    (5, u'Google Buzz'),
    (6, u'Blog'),
    (7, u'Email/IM from Friend'),
    (8, u'Colleague at Work'),
    (9, u'Other'),
    ]

GALLERY_SECTIONS = [
    (u'Basics', u'basics'),
    (u'Business', u'biz'),
    (u'Accessibility', u'accessibility'),
    (u'Typography', u'typography'),
    (u'CSS3', u'css'),
    (u'Audio', u'audio'),
    (u'Video', u'video'),
    (u'Canvas', u'canvas'),
    (u'Vector Graphics', u'svg'),
    (u'Geolocation', u'geolocation'),
    (u'Mobile', u'mobile'),
    (u'Websockets', u'websockets'),
    (u'Toolkits', u'toolkit'),
    (u'Showcase', u'showcase'),
    ]

# ---------------------------------------------------------------------------
# Utility functions

def newid():
    """
    Return a new random id that is exactly 22 characters long.
    """
    return b64encode(uuid4().bytes, altchars=',-').replace('=', '')


def currentuser():
    """
    Get the current user, or None if user isn't logged in.
    """
    if 'userid' in session and session['userid']:
        return User.query.filter_by(email=session['userid']).first()
    else:
        return None


def getuser(f):
    """
    Decorator for routes that need a logged-in user.
    """
    def wrapped(*args, **kw):
        g.user = currentuser()
        return f(*args, **kw)
    wrapped.__name__ = f.__name__
    return wrapped


# ---------------------------------------------------------------------------
# Data models and forms

class Participant(db.Model):
    """
    Participant data, as submitted from the registration form.
    """
    __tablename__ = 'participant'
    id = db.Column(db.Integer, primary_key=True)
    #: User's full name
    fullname = db.Column(db.Unicode(80), nullable=False)
    #: User's email address
    email = db.Column(db.Unicode(80), nullable=False)
    #: User's company name
    company = db.Column(db.Unicode(80), nullable=False)
    #: User's job title
    jobtitle = db.Column(db.Unicode(80), nullable=False)
    #: User's twitter id (optional)
    twitter = db.Column(db.Unicode(80), nullable=True)
    #: T-shirt size (XS, S, M, L, XL, XXL, XXXL)
    tshirtsize = db.Column(db.Integer, nullable=False, default=0)
    #: How did the user hear about this event?
    referrer = db.Column(db.Integer, nullable=False, default=0)
    #: User's reason for wanting to attend
    reason = db.Column(db.Text, nullable=False)
    #: User category, defined by a reviewer
    category = db.Column(db.Integer, nullable=False, default=0)
    #: Date the user registered
    regdate = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    #: Submitter's IP address, for logging (45 chars to accommodate an IPv6 address)
    ipaddr = db.Column(db.Text(45), nullable=False)
    #: Has the user's application been approved?
    approved = db.Column(db.Boolean, default=False, nullable=False)
    #: RSVP status codes:
    #: A = Awaiting Response
    #: Y = Yes, Attending
    #: M = Maybe Attending
    #: N = Not Attending
    rsvp = db.Column(db.Unicode(1), default='A', nullable=False)


class User(db.Model):
    """
    User account. This is different from :class:`Participant` because the email
    address here has been verified and is unique. The email address in
    :class:`Participant` cannot be unique as that is unverified. Anyone may
    submit using any email address. Users are linked to their original
    submission as participants.
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    #: Participant_id
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False, unique=True)
    #: Link to participant form submission
    participant = db.relation(Participant, primaryjoin=participant_id == Participant.id)
    #: Email id (repeated from participant.email, but unique here)
    email = db.Column(db.Unicode(80), nullable=False, unique=True)
    #: Private key, for first-time access without password
    privatekey = db.Column(db.String(22), nullable=False, unique=True, default=newid)
    #: Public UID; not clear what this could be used for
    uid = db.Column(db.String(22), nullable=False, unique=True, default=newid)
    #: Password hash
    pw_hash = db.Column(db.String(80))
    #: Is this account active?
    active = db.Column(db.Boolean, nullable=False, default=False)
    #: Date of creation
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    #: Date of first login
    firstuse_date = db.Column(db.DateTime, nullable=True)

    def _set_password(self, password):
        if password is None:
            self.pw_hash = None
        else:
            self.pw_hash = generate_password_hash(password)

    password = property(fset=_set_password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def __repr__(self):
        return '<User %s>' % (self.email)


class RegisterForm(Form):
    fullname = TextField('Full name', validators=[Required()])
    email = TextField('Email address', validators=[Required(), Email()])
    company = TextField('Company name', validators=[Required()])
    jobtitle = TextField('Job title', validators=[Required()])
    twitter = TextField('Twitter id (optional)')
    reason = TextAreaField('Your reasons for attending', validators=[Required()])


class LoginForm(Form):
    email = TextField('Email address', validators=[Required(), Email()])
    password = PasswordField('Password', validators=[Required()])

    def getuser(self, name):
        return User.query.filter_by(email=name).first()

    def validate_username(self, field):
        existing = self.getuser(field.data)
        if existing is None:
            raise ValidationError, "No user account for that email address"
        if not existing.active:
            raise ValidationError, "This user account is disabled"

    def validate_password(self, field):
        user = self.getuser(self.email.data)
        if user is None or not user.check_password(field.data):
            raise ValidationError, "Incorrect password"
        self.user = user


# ---------------------------------------------------------------------------
# Routes

@app.route('/', methods=['GET'])
@getuser
def index(**forms):
    regform = forms.get('regform', RegisterForm())
    loginform = forms.get('loginform', LoginForm())
    return render_template('index.html',
                           regform=regform,
                           loginform=loginform,
                           gallery_sections=GALLERY_SECTIONS)


@app.route('/login')
def loginkey():
    """
    Login (via access key only)
    """
    key = request.args.get('key')
    if key is None:
        return redirect(url_for('index'), code=303)
    user = User.query.filter_by(privatekey=key).first()
    if user is None:
        flash("Invalid access key", 'error')
        return redirect(url_for('index'), code=303)
    if not user.active:
        flash("This account is disabled", 'error')
        return redirect(url_for('index'), code=303)
    if user.pw_hash != '':
        # User already has a password. Can't login by key now.
        flash("This access key is not valid anymore", 'error')
        return redirect(url_for('index'), code=303)
    if user.firstuse_date is None:
        user.firstuse_date = datetime.utcnow()
        db.session.commit()
    g.user = user
    session['userid'] = user.email
    flash("You are now logged in", 'info')
    return redirect(url_for('index'), code=303)


@app.route('/logout')
def logout():
    g.user = None
    del session['userid']
    return redirect(url_for('index'), code=303)


@app.route('/rsvp')
def rsvp():
    key = request.args.get('key')
    choice = request.args.get('rsvp')
    if key is None:
        flash(u"You need an access key to RSVP.", 'error')
        return redirect(url_for('index'), code=303)
    if choice not in ['Y', 'N', 'M']:
        flash(u"You need to RSVP with Yes, No or Maybe: Y, N or M.", 'error')
        return redirect(url_for('index'), code=303)
    user = User.query.filter_by(privatekey=key).first()
    if user is None:
        flash(u"Sorry, that access key is not in our records.", 'error')
        return redirect(url_for('index'), code=303)
    user.participant.rsvp = choice
    if choice == 'Y':
        flash(u"Yay! So glad you will be joining us.", 'info')
    elif choice == 'N':
        flash(u"Sorry you can't make it. Hope you’ll join us next time.", 'error') # Fake 'error' for frowny icon
    elif choice == 'M':
        flash(u"We recorded you as Maybe Attending. When you know better, could you select Yes or No?", 'info')
    db.session.commit()
    return redirect(url_for('index'), code=303)


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'), code=301)


@app.route('/robots.txt')
def robots():
    # Disable support for indexing fragments, since there's no backing code
    return "Disallow: /*_escaped_fragment_\n"


# ---------------------------------------------------------------------------
# Form submission

@app.route('/', methods=['POST'])
def submit():
    # There's only one form, so we don't need to check which one was submitted
    formid = request.form.get('form.id')
    if formid == 'regform':
        return submit_register()
    elif formid == 'login':
        return submit_login()
    else:
        flash("Unknown form", 'error')
        redirect(url_for('index'), code=303)


def submit_register():
    # This function doesn't need parameters because Flask provides everything
    # via thread globals.
    form = RegisterForm()
    if form.validate_on_submit():
        participant = Participant()
        form.populate_obj(participant)
        participant.ipaddr = request.environ['REMOTE_ADDR']
        db.session.add(participant)
        db.session.commit()
        return render_template('regsuccess.html')
    else:
        if request.is_xhr:
            return render_template('regform.html',
                                   regform=form, ajax_re_register=True)
        else:
            flash("Please check your details and try again.", 'error')
            return index(regform=form)


def submit_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = form.user
        g.user = user
        session['userid'] = user.email
        if user.firstuse_date is None:
            user.firstuse_date = datetime.utcnow()
            db.session.commit()
        flash("You are now logged in", 'info')
        return redirect(url_for('index'), code=303)
    else:
        if request.is_xhr:
            return render_template('loginform.html',
                                   loginform=form, ajax_re_register=True)
        else:
            flash("Please check your details and try again", 'error')
            return index(loginform=form)


# ---------------------------------------------------------------------------
# Admin backend

@app.route('/admin/reasons/<key>')
def admin_reasons(key):
    if key and key in app.config['ACCESSKEY_REASONS']:
        headers = [('no', u'Sl No'), ('reason', u'Reason')] # List of (key, label)
        data = ({'no': i+1, 'reason': p.reason} for i, p in enumerate(Participant.query.all()))
        return render_template('datatable.html', headers=headers, data=data,
                               title=u'Reasons for attending')
    else:
        abort(401)


@app.route('/admin/list/<key>')
def admin_list(key):
    if key and key in app.config['ACCESSKEY_LIST']:
        headers = [('no', u'Sl No'), ('name', u'Name'), ('company', u'Company'),
                   ('jobtitle', u'Job Title')]
        data = ({'no': i+1, 'name': p.fullname, 'company': p.company,
                 'jobtitle': p.jobtitle} for i, p in enumerate(Participant.query.all()))
        return render_template('datatable.html', headers=headers, data=data,
                               title=u'List of participants')
    else:
        abort(401)


@app.route('/admin/data/<key>')
def admin_data(key, skipreason=False):
    if key and key in app.config['ACCESSKEY_DATA']:
        tz = timezone(app.config['TIMEZONE'])
        headers = [('no',       u'Sl No'),
                   ('regdate',  u'Date'),
                   ('name',     u'Name'),
                   ('email',    u'Email'),
                   ('company',  u'Company'),
                   ('jobtitle', u'Job Title'),
                   ('twitter',  u'Twitter'),
                   ('ipaddr',   u'IP Address'),
                   ('approved', u'Approved'),
                   ('RSVP',     u'RSVP'),
                   ]
        if not skipreason:
            headers.append(('reason',   u'Reason'))
        data = ({'no': i+1,
                 'regdate': utc.localize(p.regdate).astimezone(tz).strftime('%Y-%m-%d %H:%M'),
                 'name': p.fullname,
                 'email': p.email,
                 'company': p.company,
                 'jobtitle': p.jobtitle,
                 'twitter': p.twitter,
                 'ipaddr': p.ipaddr,
                 'approved': {True: 'Yes', False: 'No'}[p.approved],
                 'rsvp': {'A': u'', 'Y': u'Yes', 'M': u'Maybe', 'N': u'No'}[p.rsvp],
                 'reason': p.reason,
                 } for i, p in enumerate(Participant.query.all()))
        return render_template('datatable.html', headers=headers, data=data,
                               title=u'Participant data')
    else:
        abort(401)


@app.route('/admin/dnr/<key>')
def admin_data_no_reason(key):
    return admin_data(key, skipreason=True)


@app.route('/admin/classify/<key>', methods=['GET'])
def admin_classifyform(key):
    if key and key in app.config['ACCESSKEY_APPROVE']:
        tz = timezone(app.config['TIMEZONE'])
        return render_template('classify.html', participants=Participant.query.all(),
                               utc=utc, tz=tz, enumerate=enumerate, key=key)


@app.route('/admin/classify/<key>', methods=['POST'])
def admin_classify(key):
    if key and key in app.config['ACCESSKEY_APPROVE']:
        p = Participant.query.get(request.form['id'])
        if p:
            p.category = request.form['category']
    else:
        abort(401)


@app.route('/admin/approve/<key>', methods=['GET'])
def admin_approveform(key):
    if key and key in app.config['ACCESSKEY_APPROVE']:
        tz = timezone(app.config['TIMEZONE'])
        return render_template('approve.html', participants=Participant.query.all(),
                               utc=utc, tz=tz, enumerate=enumerate, key=key)
    else:
        abort(401)


@app.route('/admin/approve/<key>', methods=['POST'])
def admin_approve(key):
    if key and key in app.config['ACCESSKEY_APPROVE']:
        p = Participant.query.get(request.form['id'])
        if not p:
            status = "No such user"
        else:
            if 'action.undo' in request.form:
                p.approved = False
                status = 'Undone!'
                # Remove from MailChimp
                if MailChimp is not None and app.config['MAILCHIMP_API_KEY'] and app.config['MAILCHIMP_LIST_ID']:
                    mc = MailChimp(app.config['MAILCHIMP_API_KEY'])
                    try:
                        mc.listUnsubscribe(
                            id = app.config['MAILCHIMP_LIST_ID'],
                            email_address = p.email,
                            send_goodbye = False,
                            send_notify = False,
                            )
                        pass
                    except MailChimpError, e:
                        status = e.msg
                db.session.commit()
            elif 'action.approve' in request.form:
                p.approved = True
                status = "Tada!"
                mailsent = False
                # 1. Make user account and activate it
                user = makeuser(p)
                user.active = True
                # 2. Add to MailChimp
                if MailChimp is not None and app.config['MAILCHIMP_API_KEY'] and app.config['MAILCHIMP_LIST_ID']:
                    mc = MailChimp(app.config['MAILCHIMP_API_KEY'])
                    try:
                        mc.listSubscribe(
                            id = app.config['MAILCHIMP_LIST_ID'],
                            email_address = p.email,
                            merge_vars = {'FULLNAME': p.fullname,
                                          'JOBTITLE': p.jobtitle,
                                          'COMPANY': p.company,
                                          'TWITTER': p.twitter,
                                          'PRIVATEKEY': user.privatekey,
                                          'UID': user.uid},
                            double_optin = False
                            )
                    except MailChimpError, e:
                        status = e.msg
                        if e.code == 214: # Already subscribed
                            mailsent = True
                # 3. Send notice of approval
                if not mailsent:
                    msg = Message(subject="Your registration has been approved",
                                  recipients = [p.email])
                    msg.body = render_template("approve_notice.md", p=p)
                    msg.html = markdown(msg.body)
                    with app.open_resource("static/doctypehtml5.ics") as ics:
                        msg.attach("doctypehtml5.ics", "text/calendar", ics.read())
                    mail.send(msg)
                db.session.commit()
            else:
                status = 'Unknown action'
        if request.is_xhr:
            return status
        else:
            return redirect(url_for('admin_approveform', key=key), code=303)
    else:
        abort(401)


# ---------------------------------------------------------------------------
# Admin helper functions

def makeuser(participant):
    """
    Convert a participant into a user. Returns User object.
    """
    user = User.query.filter_by(email=participant.email).first()
    if user is None:
        user = User(email=participant.email, participant=participant)
        # These defaults don't get auto-added until the session is committed,
        # but we need them before, so we have to manually assign values here.
        user.privatekey = newid()
        user.uid = newid()
        db.session.add(user)
    return user


def _makeusers():
    """
    Helper function to create user accounts. Meant for one-time user only.
    """
    if MailChimp is not None and app.config['MAILCHIMP_API_KEY'] and app.config['MAILCHIMP_LIST_ID']:
        mc = MailChimp(app.config['MAILCHIMP_API_KEY'])
    else:
        mc = None
    for p in Participant.query.all():
        if p.approved:
            # Make user, but don't make account active
            user = makeuser(p)
            if mc is not None:
                mc.listSubscribe(
                    id = app.config['MAILCHIMP_LIST_ID'],
                    email_address = p.email,
                    merge_vars = {'FULLNAME': p.fullname,
                                  'JOBTITLE': p.jobtitle,
                                  'COMPANY': p.company,
                                  'TWITTER': p.twitter,
                                  'PRIVATEKEY': user.privatekey,
                                  'UID': user.uid},
                    double_optin = False,
                    update_existing = True
                    )
    db.session.commit()


# ---------------------------------------------------------------------------
# Config and startup

app.config.from_object(__name__)
try:
    app.config.from_object('settings')
except ImportError:
    import sys
    print >> sys.stderr, "Please create a settings.py with the necessary settings. See settings-sample.py."
    print >> sys.stderr, "You may use the site without these settings, but some features may not work."

# Create database table
db.create_all()

if __name__ == '__main__':
    if MailChimp is None:
        import sys
        print >> sys.stderr, "greatape is not installed. MailChimp support will be disabled."
    app.run('0.0.0.0', 8000, debug=True)
