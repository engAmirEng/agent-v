from django.db import models


class PlanType(models.TextChoices):
    DEFAULT = "def", "default"
    ONE = "one", "one"
    TWO = "two", "two"
    THREE = "three", "three"
    FOUR = "four", "four"
