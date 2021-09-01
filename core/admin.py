from django.contrib import admin
from .models import Item, OrderItem, Order, ShippingAddress, Payment, Message

admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order)
admin.site.register(Payment)
admin.site.register(ShippingAddress)
admin.site.register(Message)
