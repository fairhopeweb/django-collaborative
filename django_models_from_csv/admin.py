import importlib
import logging
import sys

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.urls.base import clear_url_caches
from django.utils.module_loading import import_module
from import_export.admin import ExportMixin
from import_export.resources import modelresource_factory

from django_models_from_csv.models import create_models
from django_models_from_csv.utils.common import get_setting


logger = logging.getLogger(__name__)


class AdminAutoRegistration:
    """
    Automatically register dynamic models. Models with a full name
    that matches the specified `include` string will be registered.

    By default, `include` is set to "django_models_from_csv.models"
    """
    def __init__(self, include="django_models_from_csv.models"):
        self.include = include

    def attempt_register(self, Model, ModelAdmin):
        try:
            admin.site.unregister(Model)
        except admin.sites.NotRegistered:
            pass
        try:
            admin.site.register(Model, ModelAdmin)
        except admin.sites.AlreadyRegistered:
            logger.warning("WARNING! %s admin already exists." % (
                str(Model)
            ))

        # If we don't do this, our module will show up in admin but
        # it will show up as an unclickable thing with on add/change
        importlib.reload(import_module(settings.ROOT_URLCONF))
        clear_url_caches()

    def get_readonly_fields(self, Model):
        return []

    def get_fields(self, Model):
        fields = []
        for f in Model._meta.get_fields():
            if f.is_relation: continue
            if not hasattr(f, "auto_created"): continue
            if f.auto_created: continue
            fields.append(f.name)
        return fields

    def create_admin(self, Model):
        name = Model._meta.object_name
        ro_fields = self.get_readonly_fields(Model)
        fields = self.get_fields(Model)
        resource = modelresource_factory(model=Model)()
        return type("%sAdmin" % name, (ExportMixin, admin.ModelAdmin,), {
            "resource_class": resource,
            # "fields": fields,
            # "readonly_fields": ro_fields,
        })

    def should_register_admin(self, Model):
        return self.include in str(Model)

    def register(self):
        try:
            create_models()
        except Exception:
            pass
        for Model in apps.get_models():
            if not self.should_register_admin(Model):
                continue

            ModelAdmin = self.create_admin(Model)
            self.attempt_register(Model, ModelAdmin)


if get_setting("CSV_MODELS_AUTO_REGISTER_ADMIN", True):
    # Auto-register Admins for all dymamic models. This avoids needing to
    # write code and inject it into an admin.py for our auto-generated
    # models
    auto_reg = AdminAutoRegistration(include="django_models_from_csv.models")
    auto_reg.register()
