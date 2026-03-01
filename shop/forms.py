from django import forms
from django.core.exceptions import ValidationError

from .models import Product, Category, Producer, Supplier, Unit


def validate_non_negative(value):
    if value is not None and value < 0:
        raise ValidationError('Значение не может быть отрицательным.')


class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label='Цена',
        error_messages={'min_value': 'Цена не может быть отрицательной.'},
    )
    quantity = forms.IntegerField(
        min_value=0,
        label='Количество на складе',
        error_messages={'min_value': 'Количество не может быть отрицательным.'},
    )
    discount = forms.IntegerField(
        min_value=0,
        max_value=100,
        label='Действующая скидка (%)',
        required=False,
        initial=0,
    )
    image_upload = forms.ImageField(
        label='Фото товара (загрузить/заменить)',
        required=False,
        help_text='Рекомендуемый размер: 300×200 px. Сохраняется в папку приложения.',
    )

    class Meta:
        model = Product
        fields = [
            'article', 'name', 'category', 'description',
            'producer', 'supplier', 'price', 'unit',
            'quantity', 'discount',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.is_edit = kwargs.pop('is_edit', False)
        super().__init__(*args, **kwargs)
        if self.is_edit:
            self.fields['article'].disabled = True
        else:
            self.fields['article'].required = True

    def clean_price(self):
        val = self.cleaned_data.get('price')
        if val is not None and val < 0:
            raise ValidationError('Цена не может быть отрицательной.')
        return val

    def clean_quantity(self):
        val = self.cleaned_data.get('quantity')
        if val is not None and val < 0:
            raise ValidationError('Количество не может быть отрицательным.')
        return val


