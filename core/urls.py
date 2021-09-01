from django.urls import path, include
from . import views

app_name = "core"

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('product/<slug>', views.ItemDetailView.as_view(), name='product'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('confirm-order/', views.ConfirmOrderView.as_view(), name='confirm-order'),
    path('orders/', views.OrdersView.as_view(), name='orders'),
    path('contact/', views.ContactView.as_view(), name='contact'),

    path('create-checkout-session/', views.CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('payment/success', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/cancel', views.PaymentCancelView.as_view(), name='payment-cancel'),

    path('webhook/stripe', views.stripe_webhook, name='stripe-webhook'),

    path('media/images/<str:filename>', views.get_images, name='get-images'),
    path('add-to-cart/<slug>', views.add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<slug>', views.remove_from_cart, name='remove-from-cart'),
    path('remove-single-item-from-cart/<slug>', views.remove_single_item_from_cart, name='remove-single-item-from-cart'),
]
