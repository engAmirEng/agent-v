from django import template

register = template.Library()


@register.filter
def separate_card_digits(value):
    """
    4 by 4
    """
    value = str(value)
    separated_digits = "-".join(value[i : i + 4] for i in range(0, len(value), 4))  # noqa
    return separated_digits
