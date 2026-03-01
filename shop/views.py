import os
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView

from PIL import Image

from .models import Product, Order, OrderItem, UserProfile
from .forms import ProductForm

User = get_user_model()

SESSION_EDITING_PRODUCT_ID = 'editing_product_id'


def get_user_role(request):
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.profile.role
    except UserProfile.DoesNotExist:
        return 'client'


def get_user_fio(request):
    if not request.user.is_authenticated:
        return ''
    try:
        return request.user.profile.full_name or request.user.get_full_name() or request.user.username
    except UserProfile.DoesNotExist:
        return request.user.get_full_name() or request.user.username


def product_image_url(product):
    if product and product.image and product.image.strip():
        path = Path(settings.MEDIA_ROOT) / product.image.strip()
        if path.exists():
            return f'{settings.MEDIA_URL}{product.image.strip()}'
    return '/static/img/picture.png'


class CustomLoginView(DjangoLoginView):
    """Окно входа: логин/пароль из БД или переход к просмотру товаров в роли гостя."""
    template_name = 'shop/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('shop:product_list')


def logout_view(request):
    """Выход на главный экран (окно входа)."""
    auth_logout(request)
    return redirect('shop:login')


def product_list(request):
    """Список товаров. Гость/клиент: без фильтрации, сортировки, поиска. Менеджер/админ: с поиском, сортировкой, фильтром по поставщику."""
    role = get_user_role(request)
    can_search_sort_filter = role in (UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN)

    qs = Product.objects.select_related('category', 'producer', 'supplier', 'unit').all()

    search = request.GET.get('search', '').strip()
    supplier_id = request.GET.get('supplier', '')
    sort = request.GET.get('sort', '')

    if can_search_sort_filter:
        if search:
            qs = qs.filter(
                Q(article__icontains=search) |
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search) |
                Q(producer__name__icontains=search) |
                Q(supplier__name__icontains=search)
            )
        if supplier_id:
            qs = qs.filter(supplier_id=int(supplier_id))
        if sort == 'quantity_asc':
            qs = qs.order_by('quantity')
        elif sort == 'quantity_desc':
            qs = qs.order_by('-quantity')

    suppliers = list(qs.values_list('supplier_id', 'supplier__name').distinct()) if not can_search_sort_filter else []
    if can_search_sort_filter:
        from .models import Supplier
        suppliers = list(Supplier.objects.values_list('id', 'name').order_by('name'))

    product_list_with_images = []
    for p in qs:
        p.image_url = product_image_url(p)
        product_list_with_images.append(p)

    context = {
        'product_list': product_list_with_images,
        'role': role,
        'user_fio': get_user_fio(request),
        'can_search_sort_filter': can_search_sort_filter,
        'search': search,
        'supplier_id': supplier_id,
        'sort': sort,
        'suppliers': suppliers,
    }
    return render(request, 'shop/product_list.html', context)


@login_required
def order_list(request):
    """Список заказов для менеджера и администратора."""
    role = get_user_role(request)
    if role not in (UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN):
        messages.error(request, 'Доступ запрещён. Просматривать заказы могут только менеджер и администратор.')
        return redirect('shop:product_list')

    orders = Order.objects.prefetch_related('items__product').select_related('pickup_point').all()
    context = {
        'order_list': orders,
        'role': role,
        'user_fio': get_user_fio(request),
    }
    return render(request, 'shop/order_list.html', context)


def product_image_url_for_template(product):
    return product_image_url(product)


def product_edit_dispatch(request, pk=None):
    """Редактирование товара (pk) или добавление (pk=None). Только администратор. Одно окно редактирования."""
    role = get_user_role(request)
    if role != UserProfile.ROLE_ADMIN:
        messages.error(request, 'Добавлять и редактировать товары может только администратор.')
        return redirect('shop:product_list')

    editing_id = request.session.get(SESSION_EDITING_PRODUCT_ID)
    if pk:
        product = get_object_or_404(Product, pk=pk)
        if editing_id is not None and int(editing_id) != product.pk:
            messages.warning(
                request,
                'Невозможно открыть более одного окна редактирования. Сохраните или отмените текущее редактирование.',
            )
            return redirect('shop:product_list')
        request.session[SESSION_EDITING_PRODUCT_ID] = product.pk
        is_edit = True
    else:
        product = None
        if editing_id is not None:
            messages.warning(
                request,
                'Сначала закройте окно редактирования товара (сохраните или нажмите «Назад»).',
            )
            return redirect('shop:product_list')
        request.session[SESSION_EDITING_PRODUCT_ID] = -1
        is_edit = False

    if request.method == 'POST':
        if 'cancel' in request.POST:
            request.session.pop(SESSION_EDITING_PRODUCT_ID, None)
            return redirect('shop:product_list')
        form = ProductForm(request.POST, request.FILES, instance=product, is_edit=is_edit)
        if form.is_valid():
            if is_edit:
                obj = form.save(commit=False)
                old_image = obj.image
            else:
                from .models import Category, Unit, Producer, Supplier
                obj = Product(
                    article=form.cleaned_data['article'],
                    name=form.cleaned_data['name'],
                    category=form.cleaned_data['category'],
                    description=form.cleaned_data['description'] or '',
                    producer=form.cleaned_data['producer'],
                    supplier=form.cleaned_data['supplier'],
                    price=form.cleaned_data['price'],
                    unit=form.cleaned_data['unit'],
                    quantity=form.cleaned_data['quantity'],
                    discount=form.cleaned_data['discount'] or 0,
                    image='',
                )
                obj.save()
                old_image = None

            image_file = request.FILES.get('image_upload')
            if image_file:
                media_root = Path(settings.MEDIA_ROOT)
                media_root.mkdir(parents=True, exist_ok=True)
                products_dir = media_root / 'products'
                products_dir.mkdir(exist_ok=True)
                ext = Path(image_file.name).suffix or '.jpg'
                filename = f'product_{obj.article}_{obj.pk}{ext}'
                filepath = products_dir / filename
                with open(filepath, 'wb') as f:
                    for chunk in image_file.chunks():
                        f.write(chunk)
                try:
                    img = Image.open(filepath)
                    img.thumbnail((300, 200), Image.Resampling.LANCZOS)
                    img.save(filepath, quality=85)
                except Exception:
                    pass
                if old_image and old_image.strip():
                    old_path = media_root / old_image.strip()
                    if old_path.exists():
                        try:
                            old_path.unlink()
                        except OSError:
                            pass
                obj.image = f'products/{filename}'
            obj.save()
            request.session.pop(SESSION_EDITING_PRODUCT_ID, None)
            messages.success(request, 'Товар успешно сохранён.')
            return redirect('shop:product_list')

        messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = ProductForm(instance=product, is_edit=is_edit)
        if is_edit and product:
            form.fields['article'].initial = product.article

    context = {
        'form': form,
        'product': product,
        'is_edit': is_edit,
        'user_fio': get_user_fio(request),
        'product_image_url': product_image_url(product) if product else '/static/img/picture.png',
    }
    return render(request, 'shop/product_form.html', context)


def product_add(request):
    return product_edit_dispatch(request, pk=None)


def product_edit(request, pk):
    return product_edit_dispatch(request, pk=pk)


def product_delete(request, pk):
    role = get_user_role(request)
    if role != UserProfile.ROLE_ADMIN:
        messages.error(request, 'Удалять товары может только администратор.')
        return redirect('shop:product_list')

    product = get_object_or_404(Product, pk=pk)
    if OrderItem.objects.filter(product=product).exists():
        messages.error(
            request,
            f'Товар «{product.name}» нельзя удалить: он присутствует в заказе. Сначала удалите позиции заказа или заказ.',
        )
        return redirect('shop:product_list')

    old_image = product.image
    product.delete()
    if old_image and old_image.strip():
        media_root = Path(settings.MEDIA_ROOT)
        old_path = media_root / old_image.strip()
        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass
    request.session.pop(SESSION_EDITING_PRODUCT_ID, None)
    messages.success(request, 'Товар удалён.')
    return redirect('shop:product_list')
