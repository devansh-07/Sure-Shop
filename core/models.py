from django.db import models
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django_countries.fields import CountryField

User = get_user_model()

CATEGOGY_CHOICES = (
    ('M', 'Mobiles'),
    ('B', 'Books'),
    ('C', 'Clothing'),
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger'),
)

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="images/")
    discount_price = models.FloatField(blank=True, null=True)
    price = models.FloatField()
    category = models.CharField(choices=CATEGOGY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug = models.SlugField()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })

    def get_final_price(self):
        if self.discount_price:
            return self.discount_price
        else:
            return self.price

class OrderItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="order_item_count")
    ordered = models.BooleanField(default=False)

    def get_saved_amount(self):
        if self.item.discount_price:
            return self.quantity * (self.item.price - self.item.discount_price)
        else:
            return 0

    def get_final_cost(self):
        return self.quantity * self.item.get_final_price()

    def __str__(self):
        return f"{self.item.name} - {self.quantity}"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_orders")
    items = models.ManyToManyField(OrderItem)
    ordered = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField(blank=True, null=True)
    shipping_address = models.ForeignKey('ShippingAddress', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, blank=True, null=True)

    def get_total(self):
        total = 0
        for orderitem in self.items.all():
            total += orderitem.get_final_cost()

        return total

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_shipping_address")
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=10)

    def __str__(self):
        return self.user.username

    def get_complete_address(self):
        address = ", ".join([self.street_address, self.apartment_address]) if self.apartment_address else self.street_address
        return ", ".join([self.user.first_name, address, self.zip, self.country.name])

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="user_payments", null=True)
    stripe_payment_id = models.CharField(max_length=100)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.amount)

class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="user_messages", null=True)
    subject = models.CharField(max_length=100)
    message = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject
