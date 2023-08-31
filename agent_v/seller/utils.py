import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict

from django.db import models

if TYPE_CHECKING:
    from .models import Plan


class PlanType(models.TextChoices):
    DEFAULT = "def", "default"
    ONE = "one", "one"
    TWO = "two", "two"
    THREE = "three", "three"
    FOUR = "four", "four"


class ProfileDataType(TypedDict):
    current_plan: "Plan"
    remained_data: Decimal
    expiry_date: datetime.date
