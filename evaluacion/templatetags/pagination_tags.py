from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Reemplaza o añade un parámetro de consulta a la URL actual,
    preservando los demás parámetros.
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

