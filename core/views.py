from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, View, TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from .models import *
from .forms import *
import os

import stripe

stripe.api_key = settings.STRIPE_API_KEY

def get_images(request, filename):
    return FileResponse(open(os.path.join(os.getcwd(), 'Media/images/', filename), 'rb'))

class ContactView(View):
    def get(self, *args, **kwargs):
        form = ContactForm()
        context = {
            'form': form,
        }
        return render(self.request, "core/contact.html", context)

    def post(self, *args, **kwargs):
        form = ContactForm(self.request.POST or None)

        if form.is_valid():
            message = form.save(self.request)
            messages.info(self.request, "Message has been sent.")
        else:
            messages.warning(self.request, "Invalid attempt.")

        return redirect("core:home")

class OrdersView(View):
    def get(self, *args, **kwargs):
        orders = Order.objects.filter(user=self.request.user, ordered=True).order_by('-ordered_date')
        context = {
            'orders': orders,
        }
        return render(self.request, "core/orders.html", context)

class HomeView(ListView):
    model = Item
    paginate_by = 8
    template_name = "core/home.html"

    def get_context_data(self):
        category = self.request.GET.get("category")
        if category:
            items = Item.objects.filter(category=category)
        else:
            items = Item.objects.all()

        context = {
            'object_list': items,
            'categories': Item.category.field.choices,
            'selected_category': category
        }

        return context

class ItemDetailView(DetailView):
    model = Item
    template_name = "core/product_details.html"

class PaymentSuccessView(View):
    def get(self, *args, **kwargs):
        messages.success(self.request, "Order placed successfully.")
        return redirect("core:home")

class PaymentCancelView(TemplateView):
    def get(self, *args, **kwargs):
        messages.error(self.request, "Checkout cancelled.")
        return redirect("core:home")

class ConfirmOrderView(View):
    def get(self, *args, **kwargs):
        try:
            context = {
                'order': Order.objects.get(user=self.request.user, ordered=False)
            }

            return render(self.request, "core/confirm_order.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You don't have an active order")
            return redirect("/")

        return render(self.request, "core/confirm_order.html", context)

class CartView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                "object": order
            }
        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an active order")
            return redirect("/")

        return render(self.request, "core/cart.html", context)

class CheckoutView(View):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        context = {
            'form': form,
        }
        return render(self.request, "core/checkout.html", context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)

        try:
            order = Order.objects.get(user=self.request.user, ordered=False)

            if form.is_valid():
                data = form.cleaned_data
                shipping_address = form.save(self.request)

                order.shipping_address = shipping_address
                order.save()

                if data['payment_option'] == "S":
                    return redirect('core:confirm-order')
                else:
                    messages.warning(self.request, "Invalid Payment option.")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request, "You don't have an active order")
            return redirect("/")

        messages.warning(self.request, "Checkout Failed")
        return redirect('core:checkout')

class CreateCheckoutSessionView(View):
    def post(self, *args, **kwargs):
        BASE_DOMAIN = "http://sure-shop.herokuapp.com/payment"

        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            currency= 'inr'

            items = []
            products = []

            for orderitem in order.items.all():
                d = {
                    'price_data': {
                        'currency': currency,
                        'unit_amount': int(orderitem.item.get_final_price() * 100),
                        'product_data': {
                            'name': orderitem.item.name,
                        }
                    },
                    'quantity': orderitem.quantity,
                }

                items.append(d)
                products.append(orderitem.item.slug)

            checkout_session = stripe.checkout.Session.create(
                line_items = items,

                metadata = {
                    "order_id": order.id
                },
                payment_method_types = ['card'],
                mode = 'payment',

                success_url = BASE_DOMAIN + '/success',
                cancel_url = BASE_DOMAIN + '/cancel',
            )

            return redirect(checkout_session.url)
        except Exception as e:
            print("Exception occured:", str(e))
            return HttpResponse(self.request, str(e))

        return redirect("core:checkout")

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        fulfill_order(session)

    return HttpResponse(status=200)

def fulfill_order(session):
    customer_email = session["customer_details"]["email"]
    order_id = session["metadata"]["order_id"]

    order = Order.objects.get(id=order_id)

    payment = Payment()
    payment.stripe_payment_id = session["id"]
    payment.user = order.user
    payment.amount = int(session["amount_total"])/100
    payment.save()

    order.ordered = True
    order.payment = payment
    order.ordered_date = timezone.now()
    order.save()

    order_items = order.items.all()
    order_items.update(ordered=True)
    for item in order_items:
        item.save()

    order_details = []
    for orderitem in order_items:
        order_details.append(f"{orderitem.quantity} X {orderitem.item.name}")

    all_orders = "\n".join(order_details)

    send_mail(
        subject="Order Confirmation",
        message=f"Thanks for your purchase. \nFind your order details below:\n{all_orders}",
        recipient_list=[customer_email],
        from_email="devansh@gmail.com",
    )

    print("Email sent to", customer_email)
    return

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)

    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs.first()

        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item quantity updated.")
        else:
            order.items.add(order_item)
            messages.info(request, "Item added to the Cart.")
    else:
        order = Order.objects.create(user=request.user)
        order.items.add(order_item)
        order.save()
        messages.info(request, "Item added to the Cart.")

    return redirect("core:cart")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs.first()

        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item, _ = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "Item removed from Cart.")
        else:
            # Item not present in order
            messages.warning(request, "Item not present in Cart.")
    else:
        # User doesn't have an order
        messages.warning(request, "You don't have an active order")

    return redirect("core:cart")

@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order = order_qs.first()

        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item, _ = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
            order_item.quantity -= 1
            order_item.save()

            if order_item.quantity == 0:
                order.items.remove(order_item)
                order_item.delete()

            messages.info(request, "Item Quantity decreased.")
        else:
            # Item not present in order
            messages.warning(request, "Item not present in Cart.")
    else:
        # User doesn't have an order
        messages.warning(request, "You don't have an active order")

    return redirect("core:cart")
