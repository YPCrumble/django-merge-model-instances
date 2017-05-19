from django.db import transaction
from django.db.models import Model
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.fields.related import ManyToManyField


@transaction.atomic()
def merge_model_objects(primary_object, alias_objects=None, keep_old=False):
    """Merge several model instances into one, the `primary_object`.
    Use this function to merge model objects and migrate all of the related
    fields from the alias objects the primary object.
    Usage:
        from django.contrib.auth.models import User
        primary_user = User.objects.get(email='good@example.com')
        duplicate_user = User.objects.get(email='good+duplicate@example.com')
        merge(primary_user, duplicate_user)
    Based on: https://djangosnippets.org/snippets/382/
    """
    if not alias_objects:
        alias_objects = []
    if not isinstance(alias_objects, list):
        alias_objects = [alias_objects]

    # check that all aliases are the same class as primary one and that
    # they are subclass of model
    primary_class = primary_object.__class__

    if not issubclass(primary_class, Model):
        raise TypeError('Only django.db.models.Model subclasses can be merged')

    for alias_object in alias_objects:
        if not isinstance(alias_object, primary_class):
            raise TypeError('Only models of same class can be merged')

    generic_fields = get_generic_fields()

    # get related fields
    many_to_many_fields, related_fields = discrimine(
        lambda field: isinstance(field, ManyToManyField),
        primary_object._meta._get_fields(forward=False, include_hidden=True)
    )

    blank_local_fields = set(
            [field.attname for field in primary_object._meta.local_fields
                if getattr(primary_object, field.attname) in [None, '']])

    # Loop through all alias objects and migrate their references to the
    # primary object
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary
        # object.
        for related_object in related_fields:
            # The variable name on the alias_object model.
            alias_varname = related_object.get_accessor_name()
            # The variable name on the related model.
            obj_varname = related_object.field.name
            related_objects = getattr(alias_object, alias_varname)
            if hasattr(related_objects, 'all'):
                for obj in related_objects.all():
                    setattr(obj, obj_varname, primary_object)
                    obj.save()
            else:
                # `related_objects` is a one-to-one field.
                # Merge related one-to-one fields.
                alias_related_object = related_objects
                primary_related_object = getattr(primary_object, alias_varname)
                # The delete will cascade later if `keep_old` is False.
                # Otherwise, could violate a not-null one-to-one
                # field constraint.
                merge_model_objects(
                        primary_related_object,
                        alias_related_object,
                        keep_old=True
                        )

        # Migrate all many to many references from alias object to primary
        # object.
        for related_many_object in many_to_many_fields:
            alias_varname = related_many_object.get_accessor_name()
            obj_varname = related_many_object.field.name
            if alias_varname is not None:
                # standard case
                related_many_objects = getattr(alias_object, alias_varname)
            else:
                # special case, symmetrical relation, no reverse accessor
                related_many_objects = getattr(alias_object, obj_varname)
            for obj in related_many_objects.all():
                getattr(obj, obj_varname).remove(alias_object)
                getattr(obj, obj_varname).add(primary_object)

        # Migrate all generic foreign key references from alias object to
        # primary object.
        for field in generic_fields:
            filter_kwargs = {}
            filter_kwargs[field.fk_field] = alias_object._get_pk_val()
            filter_kwargs[field.ct_field] = field.get_content_type(
                    alias_object)
            related_objects = field.model.objects.filter(**filter_kwargs)
            for generic_related_object in related_objects:
                setattr(generic_related_object, field.name, primary_object)
                generic_related_object.save()

        # Try to fill all missing values in primary object
        # by values of duplicates
        filled_up = set()
        for field_name in blank_local_fields:
            val = getattr(alias_object, field_name)
            if val not in [None, '']:
                setattr(primary_object, field_name, val)
                filled_up.add(field_name)
        blank_local_fields -= filled_up

        if alias_object.id and keep_old is False:
            alias_object.delete()

    # TODO: Is this save necessary?
    primary_object.save()
    return primary_object


def get_generic_fields():
    """Return a list of all GenericForeignKeys in all models."""
    generic_fields = []
    for model in apps.get_models():
        for field_name, field in model.__dict__.items():
            if isinstance(field, GenericForeignKey):
                generic_fields.append(field)
    return generic_fields


def discrimine(pred, sequence):
    """Split a collection in two collections using a predicate.

    >>> discrimine(lambda x: x < 5, [3, 4, 5, 6, 7, 8])
    ... ([3, 4], [5, 6, 7, 8])
    """
    positive, negative = [], []
    for item in sequence:
        if pred(item):
            positive.append(item)
        else:
            negative.append(item)
    return positive, negative
