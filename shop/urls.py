from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'shop'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='shop:login', permanent=False), name='root'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('products/', views.product_list, name='product_list'),
    path('orders/', views.order_list, name='order_list'),
    path('product/add/', views.product_add, name='product_add'),
    path('product/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
]
