#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Website server for doctypehtml5.in
"""

from __future__ import with_statement
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from base64 import b64encode
from flask import Flask, abort, request, render_template, redirect, url_for
from flask import flash, session, g
from werkzeug import generate_password_hash, check_password_hash, UserAgent
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.mail import Mail, Message
from flaskext.wtf import Form, TextField, TextAreaField, PasswordField
from flaskext.wtf import SelectField, Required, Email, ValidationError
from pytz import utc, timezone
from markdown import markdown
import pygooglechart
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
    ('0', u'Unclassified'),
    ('1', u'Student or Trainee'),
    ('2', u'Developer'),
    ('3', u'Designer'),
    ('4', u'Manager, Senior Developer/Designer'),
    ('5', u'CTO, CIO, CEO'),
    ('6', u'Entrepreneur'),
    ]

USER_CITIES = [
    ('', ''),
    ('bangalore', 'Bangalore - October 9, 2010 (over!)'),
    ('chennai', 'Chennai - November 27, 2010 (over!)'),
    ('pune', 'Pune - December 4, 2010 (closed)'),
    ('hyderabad', 'Hyderabad - January 22, 2011'),
    ]

TSHIRT_SIZES = [
    ('',  u''),
    ('1', u'XS'),
    ('2', u'S'),
    ('3', u'M'),
    ('4', u'L'),
    ('5', u'XL'),
    ('6', u'XXL'),
    ('7', u'XXXL'),
    ]

REFERRERS = [
    ('',   u''),
    ('1',  u'Twitter'),
    ('2',  u'Facebook'),
    ('3',  u'LinkedIn'),
    ('10', u'Discussion Group or List'),
    ('4',  u'Google/Bing Search'),
    ('5',  u'Google Buzz'),
    ('6',  u'Blog'),
    ('7',  u'Email/IM from Friend'),
    ('8',  u'Colleague at Work'),
    ('9',  u'Other'),
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
    #: Edition of the event they'd like to attend
    edition = db.Column(db.Unicode(80), nullable=False)
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
    #: User agent with which the user registered
    useragent = db.Column(db.Unicode(250), nullable=True)
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
    #: Did the participant attend the event?
    attended = db.Column(db.Boolean, default=False, nullable=False)
    #: Datetime the participant showed up
    attenddate = db.Column(db.DateTime, nullable=True)
    #: Did the participant agree to subscribe to the newsletter?
    subscribe = db.Column(db.Boolean, default=False, nullable=False)
    #: User_id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, unique=False)
    #: Link to user account
    user = db.relation('User', backref='participants')


class User(db.Model):
    """
    User account. This is different from :class:`Participant` because the email
    address here has been verified and is unique. The email address in
    :class:`Participant` cannot be unique as that is unverified. Anyone may
    submit using any email address. Participant objects link to user objects
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    #: User's name
    fullname = db.Column(db.Unicode(80), nullable=False)
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
    edition = SelectField('Edition', validators=[Required()], choices=USER_CITIES)
    company = TextField('Company name (or school/college)', validators=[Required()])
    jobtitle = TextField('Job title', validators=[Required()])
    twitter = TextField('Twitter id (optional)')
    tshirtsize = SelectField('T-shirt size', validators=[Required()], choices=TSHIRT_SIZES)
    referrer = SelectField('How did you hear about this event?', validators=[Required()], choices=REFERRERS)
    reason = TextAreaField('Your reasons for attending', validators=[Required()])

    def validate_edition(self, field):
        if hasattr(self, '_venuereg'):
            if field.data != self._venuereg:
                raise ValidationError, "You can't register for that"
            else:
                return # Register at venue even if public reg is closed
        if field.data in [u'bangalore', u'chennai', u'pune']:
            raise ValidationError, "Registrations are closed for this edition"


class AccessKeyForm(Form):
    key = PasswordField('Access Key', validators=[Required()])


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


@app.route('/rsvp/<edition>')
def rsvp(edition):
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
    participant = Participant.query.filter_by(user=user, edition=edition).first()
    if participant:
        participant.rsvp = choice
    else:
        flash(u"You did not register for this edition, %s." % user.fullname, 'error')
        return redirect(url_for('index'), code=303)
    if choice == 'Y':
        flash(u"Yay! So glad you will be joining us, %s." % user.fullname , 'info')
    elif choice == 'N':
        flash(u"Sorry you can't make it, %s. Hope you’ll join us next time." % user.fullname, 'error') # Fake 'error' for frowny icon
    elif choice == 'M':
        flash(u"We recorded you as Maybe Attending, %s. When you know better, could you select Yes or No?" % user.fullname, 'info')
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
        participant.useragent = request.user_agent.string
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

def adminkey(keyname):
    def decorator(f):
        def inner(edition):
            form = AccessKeyForm()
            keylist = app.config[keyname]
            # check for key and call f or return form
            if 'key' in request.values:
                if request.values.get('key') in keylist:
                    session[keyname] = request.values['key']
                    return redirect(request.base_url, code=303) # FIXME: Redirect to self URL
                else:
                    flash("Invalid access key", 'error')
                    return render_template('accesskey.html', keyform=form)
            elif keyname in session and session[keyname] in keylist:
                return f(edition)
            else:
                return render_template('accesskey.html', keyform=form)
        inner.__name__ = f.__name__
        return inner
    return decorator


@app.route('/admin/reasons/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_REASONS')
def admin_reasons(edition):
    headers = [('no', u'Sl No'), ('reason', u'Reason')] # List of (key, label)
    data = ({'no': i+1, 'reason': p.reason} for i, p in
            enumerate(Participant.query.filter_by(edition=edition)))
    return render_template('datatable.html', headers=headers, data=data,
                           title=u'Reasons for attending')


@app.route('/admin/list/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_LIST')
def admin_list(edition):
    headers = [('no', u'Sl No'), ('name', u'Name'), ('company', u'Company'),
               ('jobtitle', u'Job Title'), ('twitter', 'Twitter'),
               ('approved', 'Approved'), ('rsvp', 'RSVP'), ('attended', 'Attended')]
    data = ({'no': i+1, 'name': p.fullname, 'company': p.company,
             'jobtitle': p.jobtitle,
             'twitter': p.twitter,
             'approved': p.approved,
             'rsvp': {'Y': 'Yes', 'N': 'No', 'M': 'Maybe', 'A': 'Awaiting'}[p.rsvp],
             'attended': ['No', 'Yes'][p.attended]
             } for i, p in enumerate(Participant.query.order_by('fullname').filter_by(edition=edition)))
    return render_template('datatable.html', headers=headers, data=data,
                           title=u'List of participants')

@app.route('/admin/rsvp/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_LIST')
def admin_rsvp(edition):
   rsvp_yes = Participant.query.filter_by(edition=edition, approved=True, rsvp='Y').count()
   rsvp_no = Participant.query.filter_by(edition=edition, approved=True, rsvp='N').count()
   rsvp_maybe = Participant.query.filter_by(edition=edition, approved=True, rsvp='M').count()
   rsvp_awaiting = Participant.query.filter_by(edition=edition, approved=True, rsvp='A').count()

   return render_template('rsvp.html', yes=rsvp_yes, no=rsvp_no,
                          maybe=rsvp_maybe, awaiting=rsvp_awaiting,
                          title=u'RSVP Statistics')


@app.route('/admin/stats/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_LIST')
def admin_stats(edition):

    # Chart sizes
    CHART_X = 800
    CHART_Y = 370

    all_browsers = defaultdict(int)
    all_brver = defaultdict(int)
    all_platforms = defaultdict(int)
    present_browsers = defaultdict(int)
    present_brver = defaultdict(int)
    present_platforms = defaultdict(int)

    c_all = 0
    c_present = 0

    for p in Participant.query.filter_by(edition=edition):
        if p.useragent:
            c_all += 1
            ua = UserAgent(p.useragent)
            all_browsers[ua.browser] += 1
            all_brver['%s %s' % (ua.browser, ua.version.split('.')[0])] += 1
            all_platforms[ua.platform] += 1
    for p in Participant.query.filter_by(edition=edition, attended=True):
        if p.useragent:
            c_present += 1
            ua = UserAgent(p.useragent)
            present_browsers[ua.browser] += 1
            present_brver['%s %s' % (ua.browser, ua.version.split('.')[0])] += 1
            present_platforms[ua.platform] += 1

    if c_all != 0: # Avoid divide by zero situation
        f_all = 100.0 / c_all
    else:
        f_all = 1

    if c_present != 0: # Avoid divide by zero situation
        f_present = 100.0 / c_present
    else:
        f_present = 1

    # Now make charts
    # All registrations
    c_all_browsers = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_all_browsers.add_data(all_browsers.values())
    c_all_browsers.set_pie_labels(['%s (%.2f%%)' % (key, all_browsers[key]*f_all) for key in all_browsers.keys()])

    c_all_brver = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_all_brver.add_data(all_brver.values())
    c_all_brver.set_pie_labels(['%s (%.2f%%)' % (key, all_brver[key]*f_all) for key in all_brver.keys()])

    c_all_platforms = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_all_platforms.add_data(all_platforms.values())
    c_all_platforms.set_pie_labels(['%s (%.2f%%)' % (key, all_platforms[key]*f_all) for key in all_platforms.keys()])

    # Present at venue
    c_present_browsers = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_present_browsers.add_data(present_browsers.values())
    c_present_browsers.set_pie_labels(['%s (%.2f%%)' % (key, present_browsers[key]*f_present) for key in present_browsers.keys()])

    c_present_brver = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_present_brver.add_data(present_brver.values())
    c_present_brver.set_pie_labels(['%s (%.2f%%)' % (key, present_brver[key]*f_present) for key in present_brver.keys()])

    c_present_platforms = pygooglechart.PieChart2D(CHART_X, CHART_Y)
    c_present_platforms.add_data(present_platforms.values())
    c_present_platforms.set_pie_labels(['%s (%.2f%%)' % (key, present_platforms[key]*f_present) for key in present_platforms.keys()])

    return render_template('stats.html',
                           all_browsers = c_all_browsers.get_url(),
                           all_brver = c_all_brver.get_url(),
                           all_platforms = c_all_platforms.get_url(),
                           present_browsers = c_present_browsers.get_url(),
                           present_brver = c_present_brver.get_url(),
                           present_platforms = c_present_platforms.get_url()
                           )


@app.route('/admin/data/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_DATA')
def admin_data(edition):
    d_tshirt = dict(TSHIRT_SIZES)
    d_referrer = dict(REFERRERS)
    d_category = dict(USER_CATEGORIES)
    tz = timezone(app.config['TIMEZONE'])
    headers = [('no',       u'Sl No'),
               ('regdate',  u'Date'),
               ('name',     u'Name'),
               ('email',    u'Email'),
               ('company',  u'Company'),
               ('jobtitle', u'Job Title'),
               ('twitter',  u'Twitter'),
               ('tshirt',   u'T-shirt Size'),
               ('referrer', u'Referrer'),
               ('category', u'Category'),
               ('ipaddr',   u'IP Address'),
               ('approved', u'Approved'),
               ('RSVP',     u'RSVP'),
               ('agent',    u'User Agent'),
               ('reason',   u'Reason'),
               ]
    data = ({'no': i+1,
             'regdate': utc.localize(p.regdate).astimezone(tz).strftime('%Y-%m-%d %H:%M'),
             'name': p.fullname,
             'email': p.email,
             'company': p.company,
             'jobtitle': p.jobtitle,
             'twitter': p.twitter,
             'tshirt': d_tshirt.get(str(p.tshirtsize), p.tshirtsize),
             'referrer': d_referrer.get(str(p.referrer), p.referrer),
             'category': d_category.get(str(p.category), p.category),
             'ipaddr': p.ipaddr,
             'approved': {True: 'Yes', False: 'No'}[p.approved],
             'rsvp': {'A': u'', 'Y': u'Yes', 'M': u'Maybe', 'N': u'No'}[p.rsvp],
             'agent': p.useragent,
             'reason': p.reason,
             } for i, p in enumerate(Participant.query.filter_by(edition=edition)))
    return render_template('datatable.html', headers=headers, data=data,
                           title=u'Participant data')


@app.route('/admin/classify/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_APPROVE')
def admin_classify(edition):
    if request.method == 'GET':
        tz = timezone(app.config['TIMEZONE'])
        return render_template('classify.html', participants=Participant.query.filter_by(edition=edition),
                               utc=utc, tz=tz, enumerate=enumerate, edition=edition)
    elif request.method == 'POST':
        p = Participant.query.get(request.form['id'])
        if p:
            p.category = request.form['category']
        # TODO: Return status


@app.route('/admin/approve/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_APPROVE')
def admin_approve(edition):
    if request.method == 'GET':
        tz = timezone(app.config['TIMEZONE'])
        return render_template('approve.html', participants=Participant.query.filter_by(edition=edition),
                               utc=utc, tz=tz, enumerate=enumerate, edition=edition)
    elif request.method == 'POST':
        p = Participant.query.get(request.form['id'])
        if not p:
            status = "No such user"
        else:
            if 'action.undo' in request.form:
                p.approved = False
                p.user = None
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
                if p.approved:
                    status = "Already approved"
                else:
                    # Check for dupe participant (same email, same edition)
                    dupe = False
                    for other in Participant.query.filter_by(edition=p.edition, email=p.email):
                        if other.id != p.id:
                            if other.user:
                                dupe = True
                                break
                    if dupe == False:
                        p.approved = True
                        status = "Tada!"
                        # 1. Make user account and activate it
                        user = makeuser(p)
                        user.active = True
                        # 2. Add to MailChimp
                        if MailChimp is not None and app.config['MAILCHIMP_API_KEY'] and app.config['MAILCHIMP_LIST_ID']:
                            mc = MailChimp(app.config['MAILCHIMP_API_KEY'])
                            addmailchimp(mc, p)
                        # 3. Send notice of approval
                        msg = Message(subject="Your registration has been approved",
                                      recipients = [p.email])
                        msg.body = render_template("approve_notice_%s.md" % edition, p=p)
                        msg.html = markdown(msg.body)
                        with app.open_resource("static/doctypehtml5-%s.ics" % edition) as ics:
                            msg.attach("doctypehtml5.ics", "text/calendar", ics.read())
                        mail.send(msg)
                        db.session.commit()
                    else:
                        status = "Dupe"
            else:
                status = 'Unknown action'
        if request.is_xhr:
            return status
        else:
            return redirect(url_for('admin_approve', edition=edition), code=303)
    else:
        abort(401)


@app.route('/admin/venue/<edition>', methods=['GET', 'POST'])
@adminkey('ACCESSKEY_APPROVE')
def admin_venue(edition):
    if request.method == 'GET' and 'email' not in request.args:
        return render_template('venuereg.html', edition=edition)
    elif request.method =='POST' or 'email' in request.args:
        if 'email' in request.args:
            formid = 'venueregemail'
        else:
            formid = request.form.get('form.id')
        if formid == 'venueregemail':
            email = request.values.get('email')
            if email:
                p = Participant.query.filter_by(edition=edition, email=email).first()
                if p is not None:
                    if p.attended: # Already signed in
                        flash("You have already signed in. Next person please.")
                        return redirect(url_for('admin_venue', edition=edition), code=303)
                    else:
                        return render_template('venueregdetails.html', edition=edition, p=p)
            # Unknown email address. Ask for new registration
            regform = RegisterForm()
            regform.email.data = email
            regform.edition.data = edition
            return render_template('venueregnew.html', edition=edition, regform=regform)
        elif formid == 'venueregconfirm':
            id = request.form['id']
            subscribe = request.form.get('subscribe')
            p = Participant.query.get(id)
            if subscribe:
                p.subscribe = True
            else:
                p.subscribe = False
            p.attended = True
            p.attenddate = datetime.utcnow()
            db.session.commit()
            flash("You have been signed in. Next person please.", 'info')
            return redirect(url_for('admin_venue', edition=edition), code=303)
        elif formid == 'venueregform':
            # Validate form and register
            regform = RegisterForm()
            regform._venuereg = edition
            if regform.validate_on_submit():
                participant = Participant()
                regform.populate_obj(participant)
                participant.ipaddr = request.environ['REMOTE_ADDR']
                # Do not record participant.useragent since it's a venue computer, not user's.
                makeuser(participant)
                db.session.add(participant)
                if MailChimp is not None and app.config['MAILCHIMP_API_KEY'] and app.config['MAILCHIMP_LIST_ID']:
                    mc = MailChimp(app.config['MAILCHIMP_API_KEY'])
                    addmailchimp(mc, participant)
                db.session.commit()
                return render_template('venueregsuccess.html', edition=edition, p=participant)
            else:
                return render_template('venueregform.html', edition=edition,
                                       regform=regform, ajax_re_register=True)
        else:
            flash("Unknown form submission", 'error')
            return redirect(url_for('admin_venue', edition=edition), code=303)


# ---------------------------------------------------------------------------
# Admin helper functions

def makeuser(participant):
    """
    Convert a participant into a user. Returns User object.
    """
    if participant.user:
        return participant.user
    else:
        user = User.query.filter_by(email=participant.email).first()
        if user is not None:
            participant.user = user
        else:
            user = User(fullname=participant.fullname, email=participant.email)
            participant.user = user
            # These defaults don't get auto-added until the session is committed,
            # but we need them before, so we have to manually assign values here.
            user.privatekey = newid()
            user.uid = newid()
            db.session.add(user)
    return user


def _makeusers():
    """
    Helper function to create user accounts. Meant for one-time use only.
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
                addmailchimp(mc, p)
    db.session.commit()


def addmailchimp(mc, p):
    """
    Add user to mailchimp list
    """
    editions = [ap.edition for ap in p.user.participants if p.user]
    groups = {'Editions': {'name': 'Editions', 'groups': ','.join(editions)}}
    mc.listSubscribe(
        id = app.config['MAILCHIMP_LIST_ID'],
        email_address = p.email,
        merge_vars = {'FULLNAME': p.fullname,
                      'JOBTITLE': p.jobtitle,
                      'COMPANY': p.company,
                      'TWITTER': p.twitter,
                      'PRIVATEKEY': p.user.privatekey,
                      'UID': p.user.uid,
                      'GROUPINGS': groups},
        double_optin = False,
        update_existing = True
        )


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
