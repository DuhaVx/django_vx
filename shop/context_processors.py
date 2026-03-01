def shop_context(request):
    from .views import get_user_role, get_user_fio
    return {
        'role': get_user_role(request),
        'user_fio': get_user_fio(request),
    }
