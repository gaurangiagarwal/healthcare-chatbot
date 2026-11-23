"""Fail-closed settings for disposable MediReach validation only.

Activate explicitly with MEDIREACH_VALIDATION=1 and
DJANGO_SETTINGS_MODULE=config.validation_settings. This module never uses the
DATABASE_URL value supplied by the caller.
"""

import os
from pathlib import Path


if os.environ.get("MEDIREACH_VALIDATION") != "1":
    raise RuntimeError(
        "Validation settings require MEDIREACH_VALIDATION=1; refusing to start."
    )


# Fixed location outside the project directory. Settings configuration does
# not create this directory or database; create them only during the approved
# isolated-validation step.
VALIDATION_DATABASE_PATH = Path(
    r"C:\Users\zaara\Music\MediReach_Validation\validation.sqlite3"
).resolve(strict=False)

# Load the established application settings, then replace the database config
# unconditionally. This does not open a connection. A supplied DATABASE_URL
# cannot select a different database in validation mode.
from .settings import *  # noqa: E402,F401,F403


ORIGINAL_DATABASE_PATH = (BASE_DIR / "db.sqlite3").resolve(strict=False)
if VALIDATION_DATABASE_PATH == ORIGINAL_DATABASE_PATH:
    raise RuntimeError(
        "Validation database resolves to the protected project database; refusing to start."
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(VALIDATION_DATABASE_PATH),
        "OPTIONS": {"timeout": 20},
    }
}
