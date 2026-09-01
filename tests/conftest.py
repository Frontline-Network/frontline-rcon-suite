import os


# Establish the intended Django settings module before test collection imports
# RCON compatibility modules. Django itself remains lazy and is only initialized
# by tests that actually need it.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
