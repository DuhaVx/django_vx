from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CLIENT, 'Клиент'),
        (ROLE_MANAGER, 'Менеджер'),
        (ROLE_ADMIN, 'Администратор'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    full_name = models.CharField('ФИО', max_length=255)

    class Meta:
        db_table = 'shop_user_profile'

    def __str__(self):
        return self.full_name or self.user.username


class Category(models.Model):
    name = models.CharField('Наименование', max_length=255, unique=True)

    class Meta:
        db_table = 'shop_category'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField('Наименование', max_length=50, unique=True)

    class Meta:
        db_table = 'shop_unit'
        verbose_name = 'Единица измерения'
        verbose_name_plural = 'Единицы измерения'

    def __str__(self):
        return self.name


class Producer(models.Model):
    name = models.CharField('Наименование', max_length=255, unique=True)

    class Meta:
        db_table = 'shop_producer'
        verbose_name = 'Производитель'
        verbose_name_plural = 'Производители'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField('Наименование', max_length=255, unique=True)

    class Meta:
        db_table = 'shop_supplier'
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'

    def __str__(self):
        return self.name


class Product(models.Model):
    article = models.CharField('Артикул', max_length=50, unique=True, db_index=True)
    name = models.CharField('Наименование товара', max_length=255)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория товара',
    )
    description = models.TextField('Описание товара', blank=True)
    producer = models.ForeignKey(
        Producer,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Производитель',
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Поставщик',
    )
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2,
        validators=[],
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Единица измерения',
    )
    quantity = models.PositiveIntegerField('Количество на складе', default=0)
    discount = models.PositiveIntegerField(
        'Действующая скидка (%)',
        default=0,
    )
    image = models.CharField(
        'Путь к фото',
        max_length=500,
        blank=True,
        help_text='Путь к файлу изображения относительно MEDIA',
    )

    class Meta:
        db_table = 'shop_product'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['article']

    def __str__(self):
        return f'{self.article} — {self.name}'

    @property
    def final_price(self):
        if self.discount <= 0:
            return self.price
        return round(self.price * (100 - self.discount) / 100, 2)

    @property
    def has_reduced_price(self):
        return self.discount > 0


class PickupPoint(models.Model):
    address = models.CharField('Адрес', max_length=500)

    class Meta:
        db_table = 'shop_pickup_point'
        verbose_name = 'Пункт выдачи'
        verbose_name_plural = 'Пункты выдачи'

    def __str__(self):
        return self.address


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_DELIVERED, 'Доставлен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]
    number = models.CharField('Номер заказа', max_length=50, unique=True, db_index=True)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Клиент',
        null=True,
        blank=True,
    )
    client_name = models.CharField('ФИО клиента', max_length=255, blank=True)
    date_created = models.DateField('Дата создания')
    date_delivery = models.DateField('Дата доставки', null=True, blank=True)
    pickup_point = models.ForeignKey(
        PickupPoint,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Пункт выдачи',
        null=True,
        blank=True,
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    class Meta:
        db_table = 'shop_order'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-date_created']

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        db_table = 'shop_order_item'
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        unique_together = [['order', 'product']]
