import datetime
from decimal import Decimal
from typing import TypedDict

from django.db import models

from .models import Plan


class PlanType(models.TextChoices):
    DEFAULT = "def", "default"
    ONE = "one", "one"
    TWO = "two", "two"
    THREE = "three", "three"
    FOUR = "four", "four"


class ProfileDataType(TypedDict):
    current_plan: Plan
    remained_data: Decimal
    expiry_date: datetime.date
