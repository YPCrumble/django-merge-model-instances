from django.db import models


class BaseModel(models.Model):
    name = models.CharField(max_length=75)


class ModelA(BaseModel):
    pass


class ForeignKeyModel(BaseModel):
    model_a = models.ForeignKey(ModelA)


class ManyToManyModel(BaseModel):
    model_a = models.ManyToManyField(ModelA)


class OneToOneModel(BaseModel):
    model_a = models.OneToOneField(ModelA)
