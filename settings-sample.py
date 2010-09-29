#: Google Analytics tracking code
GA_CODE = 'UA-XXXXXXX-X'
#: Typekit font code, from the embed URL: http://use.typekit.com/(code).js
TYPEKIT_CODE = ''
#: Database backend
SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
#: Secret key
SECRET_KEY = 'make this something random'
#: Timezone for displayed datetimes
TIMEZONE = 'Asia/Calcutta'
#: Access keys for /admin/reasons/<key>
ACCESSKEY_REASONS = ['test']
#: Access keys for /admin/list/<key>
ACCESSKEY_LIST = ['test']
#: Access key for /admin/data/<key> and /admin/dnr/<key>
ACCESSKEY_DATA = ['test']
#: Access key for /admin/approve/<key>
ACCESSKEY_APPROVE = ['test']
#: MailChimp API key to sync participant list
#: If you don't want to use MailChimp, leave this blank
MAILCHIMP_API_KEY = ''
#: MailChimp list id to put participants in.
#: The list id can be found in the list's settings
#: or via the API
MAILCHIMP_LIST_ID = ''
#: Mail settings
#: MAIL_FAIL_SILENTLY : default True
#: MAIL_SERVER : default 'localhost'
#: MAIL_PORT : default 25
#: MAIL_USE_TLS : default False
#: MAIL_USE_SSL : default False
#: MAIL_USERNAME : default None
#: MAIL_PASSWORD : default None
#: DEFAULT_MAIL_SENDER : default None
MAIL_FAIL_SILENTLY = False
MAIL_SERVER = 'localhost'
DEFAULT_MAIL_SENDER = ('DocType HTML5', 'test@example.com')
