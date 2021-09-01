from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import ShippingAddress, Message

PAYMENT_CHOICES = (
    ("S", "Stripe"),
)

class ContactForm(forms.Form):
    subject = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control',
    }))

    message = forms.CharField(widget=forms.Textarea(attrs={
        'class':'form-control',
    }))

    def save(self, request):
        data = self.cleaned_data

        new_message = Message.objects.create(
            user = request.user,
            subject = data.get("subject"),
            message = data.get("message"),
        )
        new_message.save()

        return new_message

class CheckoutForm(forms.Form):
    street_address = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control',
        'placeholder': "1234 Main St",
    }))

    apartment_address = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control',
        'placeholder': "Apartment or Suite",
    }), required=False)

    country = CountryField(blank_label="(Choose Country)").formfield(widget=CountrySelectWidget(attrs={
        'class':'custom-select d-block w-100',
    }))

    zip = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control',
    }))

    payment_option = forms.ChoiceField(widget=forms.RadioSelect, choices=PAYMENT_CHOICES)

    def save(self, request):
        data = self.cleaned_data
        user = request.user

        street_address = data.get("street_address")
        apartment_address = data.get("apartment_address")
        country = data.get("country")
        zip = data.get("zip")
        same_shipping_address = data.get("same_shipping_address")
        save_info = data.get("save_info")
        payment_option = data.get("payment_option")

        new_shipping_address = ShippingAddress.objects.create(
            user = user,
            street_address = street_address,
            apartment_address = apartment_address,
            country = country,
            zip = zip,
        )

        new_shipping_address.save()

        return new_shipping_address
