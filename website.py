#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Website server for doctypehtml5.in
"""

from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.wtf import Form, TextField, TextAreaField
from flaskext.wtf import Required, Email


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
