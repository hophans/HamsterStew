from autostew.common import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '7qpccf4yj6zq2fosuxake5w6ixstl#y)jtf++l##$o5%&n!0e@'
ALLOWED_HOSTS = ['*']
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'hamsterstew',
        'USER': 'hamsterstew',
        'PASSWORD': '64752272',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}