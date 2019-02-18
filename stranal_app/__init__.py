# -*- coding: utf-8 -*-

"""Top-level package for Stranal_app."""

__author__ = """Nguyen Quang Huy"""
__email__ = "huy010579@gmail.com"
__version__ = "0.0.1"


from stranal_app.app import SApp, Blueprint  # noqa: F401
from stranal_app.auth import current_org, current_user, require_auth  # noqa: F401
