# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
# from django.contrib import admin

from utils import merge_model_objects


def admin_merge_models_delete(modeladmin, request, queryset):
    admin_merge_models(modeladmin, request, queryset, keep_old=False)
admin_merge_models_delete.short_description = \
        "Merge selected model objects and delete merged instances"


def admin_merge_models_keep_old(modeladmin, request, queryset):
    admin_merge_models(modeladmin, request, queryset, keep_old=True)
admin_merge_models_keep_old.short_description = \
        "Merge selected model objects and keep merged instances"


def admin_merge_models(modeladmin, request, queryset, keep_old=True):
    # order_argument = \
    # settings.MERGE_MODEL_INSTANCES.get('ORDER_ARGUMENT') or "id"
    import pdb; pdb.set_trace()
    # TODO: Get the model name and then check the order_id from settings file.
    order_argument = 'id'
    queryset = queryset.order_by(order_argument)
    primary_object = queryset[0]
    alias_objects = queryset[1:]
    merge_model_objects(primary_object, alias_objects, keep_old=keep_old)


# Dynamically import the correct modeladmin.
# Dynamically add this function to those models
mergeable_models = settings.MERGE_MODEL_INSTANCES.get('MERGEABLE_MODELS')
for mergeable_model in mergeable_models:
    import pdb; pdb.set_trace()
    model_name = mergeable_model.get('MODEL_NAME')
    admin_model_name = model_name + "Admin"
    try:
        admin_model = __import__(admin_model_name)
        admin_model.actions += [
                admin_merge_models_keep_old, admin_merge_models_delete]
    except ImportError:
        raise ImportError("""
        Admin model %s could not be imported.
        Please check your MERGE_MODELS settings and
        make sure %s matches the name of your admin model.
        """ % (model_name, admin_model_name))
