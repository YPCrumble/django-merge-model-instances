from django.contrib import admin

from models import ModelA


@admin.register(ModelA)
class ModelAAdmin(admin.ModelAdmin):
    pass
