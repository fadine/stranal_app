from flask import Flask, Blueprint as _Blueprint, has_app_context
from flask_sqlalchemy import SQLAlchemy
from stranal_app import errors
from stranal_app.config import Config
from stranal_app.model import database
from stranal_app.auth import Auth
from stranal_app.endpoints import add_resource


class SApp(Flask):
    def __init__(self, import_name, auth=Auth, db=database, **kargs):

        super(SApp, self).__init__(import_name, **kargs)

        self.config.from_object(Config())
        self.add_default_endpoints()

        if auth:
            self.auth = auth() if callable(auth) else auth
            self.auth.init_app(self)
            self.add_default_blueprints()

        if isinstance(db, SQLAlchemy):
            db.init_app(self)

        errors.init_app(self)

    def init(self):
        if hasattr(self, "auth"):

            def persist_data():
                self.auth.persist_data()
                database.session.commit()

            if has_app_context():
                persist_data()
            else:
                with self.app_context():
                    persist_data()

    def add_default_blueprints(self):
        from stranal_app.api import appbp

        self.register_blueprint(appbp)

    def add_default_endpoints(self):
        from stranal_app.api import signup_view

        self.add_url_rule("/signup", "signup", signup_view, methods=["POST"])

    def add_resource(self, modelcls, base_url=None, **options):
        add_resource(self, modelcls, base_url=base_url, **options)


class Blueprint(_Blueprint):
    def add_resource(self, modelcls, base_url=None, **options):
        add_resource(self, modelcls, base_url=base_url, **options)
