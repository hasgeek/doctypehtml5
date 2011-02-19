doctypehtml5.in
===============

Source code and templates for the website http://www.doctypehtml5.in/. To run this as a test server, simply use::

   python website.py

You will need the `Flask <http://flask.pocoo.org/>`__ framework and some
extensions. To install::

   easy_install Flask Flask-SQLAlchemy Flask-WTF Flask-Mail simplejson pytz Markdown pygooglechart

Installing into a ``virtualenv`` is strongly recommended.

License
-------

BSD and Creative Commons Attribution 3.0. See ``LICENSE.txt``.

Deployment
----------

The website is currently hosted at Dreamhost using the Passenger WSGI gateway.
To reproduce this setup, create a domain using the Dreamhost panel, then
setup the Python environment::

   mkdir -p ~/python/lib/python2.5/site-packages
   PYTHONPATH=~/python/lib/python2.5/site-packages easy_install --prefix ~/python virtualenv
   PYTHONPATH=~/python/lib/python2.5/site-packages bin/virtualenv ~/python/env --no-site-packages
   source ~/python/env/bin/activate
   easy_install Flask Flask-SQLAlchemy Flask-WTF Flask-Mail simplejson pytz mysql-python greatape Markdown pygooglechart

This creates a ``virtualenv`` in ``~/python/env``, activates it, then installs
Flask and extensions in the ``virtualenv``. Dreamhost does not have
``virtualenv`` pre-installed, so it is necessary to install it first.
Dreamhost does not support ``mod_wsgi`` either, which would have made all this
much simpler.

If your site is located at (for example) ``~/doctypehtml5.in``, install the
source files there. Do not install in the ``public`` sub-folder. Dreamhost will
automatically pick up ``passenger_wsgi.py`` and start serving the site.

To refresh after updating, you must edit the site via the control panel and
click 'Save' again.

Why use a framework?
--------------------

The website is currently a single HTML page, so why use a framework at all?
Because there is also a sizeable backend that sends email and tracks responses
from participants. This is not exposed to the UI, but you can see it here in
the code.
