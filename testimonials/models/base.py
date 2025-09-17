import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from ..conf import app_settings


class UUIDModel(models.Model):
    """
    An abstract base model that uses UUID as the primary key.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID")
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    An abstract base model that provides self-updating created and modified
    timestamps.
    """
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("Updated at")
    )

    class Meta:
        abstract = True


class AutoFieldBaseModel(TimeStampedModel):
    """
    Base model using traditional AutoField primary key.
    """
    # Let Django create the default id field automatically
    # No need to explicitly define it
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDBaseModel(UUIDModel, TimeStampedModel):
    """
    Base model using UUID primary key.
    """
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


# Choose the base model based on settings
if app_settings.USE_UUID:
    BaseModel = UUIDBaseModel
else:
    BaseModel = AutoFieldBaseModel