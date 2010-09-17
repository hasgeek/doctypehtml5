#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Website server for doctypehtml5.in
"""

from datetime import datetime
from flask import Flask, abort, request, render_template, redirect, url_for
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.wtf import Form, TextField, TextAreaField
from flaskext.wtf import Required, Email
from pytz import utc, timezone

app = Flask(__name__)
db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# Data models and forms

class Participant(db.Model):
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
    #tshirtsize = db.Column(db.Unicode(1))
    #: User's reason for wanting to attend
    reason = db.Column(db.Text, nullable=False)
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


class RegisterForm(Form):
    fullname = TextField('Full name', validators=[Required()])
    email = TextField('Email address', validators=[Required(), Email()])
    company = TextField('Company name', validators=[Required()])
    jobtitle = TextField('Job title', validators=[Required()])
    twitter = TextField('Twitter id (optional)')
    reason = TextAreaField('Your reasons for attending', validators=[Required()])


# ---------------------------------------------------------------------------
# Routes

@app.route('/', methods=['GET'])
def index():
    regform = RegisterForm()
    return render_template('index.html', regform=regform)

@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'), code=301)


# ---------------------------------------------------------------------------
# Form submission

@app.route('/', methods=['POST'])
def submit():
    # There's only one form, so we don't need to check which one was submitted
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
            # TODO: This changes URL. It shouldn't.
            return render_template('index.html', regform=form)


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
    app.run('0.0.0.0', 8000, debug=True)
