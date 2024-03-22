from datetime import timedelta
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from .models import Profile
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from werkzeug.routing import ValidationError

from .models import Payment2, Bid, Shoe


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2',)


class SignInForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Your Username',
        'id': 'username',
        'required': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Your Password',
        'id': 'password',
        'required': True}))


class PaymentForm(forms.Form):
    amount = forms.DecimalField(
        decimal_places=2,
        max_digits=10,
        widget=forms.HiddenInput()  # This will make the field hidden
    )


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['bid_amount']
        widgets = {
            'bid_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item', None)
        super(BidForm, self).__init__(*args, **kwargs)
        if self.item:
            self.fields['bid_amount'].widget.attrs['min'] = str(self.item.base_price + Decimal('0.01'))


class ShoeForm(forms.ModelForm):
    auction_duration_days = forms.IntegerField(min_value=0, initial=0, help_text='Days', required=False)
    auction_duration_hours = forms.IntegerField(min_value=0, max_value=23, initial=0, help_text='Hours', required=False)
    auction_duration_minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, help_text='Minutes',
                                                  required=False)

    class Meta:
        model = Shoe
        fields = ['title', 'description', 'base_price', 'image', 'size']

    def save(self, commit=True):
        # Before saving the Shoe model instance, calculate the auction_duration
        # from the provided days, hours, and minutes.
        days = self.cleaned_data.get('auction_duration_days', 0)
        hours = self.cleaned_data.get('auction_duration_hours', 0)
        minutes = self.cleaned_data.get('auction_duration_minutes', 0)

        # Calculate the total duration
        total_duration = timedelta(days=days, hours=hours, minutes=minutes)

        # Set the auction_duration on the model instance
        self.instance.auction_duration = total_duration

        # Now save the model instance
        return super(ShoeForm, self).save(commit=commit)


class UserUpdateForm(UserChangeForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['images']


PAYMENT_CHOICES = [
    ('S', 'Stripe'),

    # Add other payment options here if needed
]


class CheckoutForm(forms.Form):
    street_address = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': '1234 Main St',
        'class': 'form-control'
    }))
    apartment_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartment or suite',
        'class': 'form-control'
    }))
    country = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Country',
        'class': 'form-control'
    }))
    zip = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Zip code',
        'class': 'form-control'
    }))
    same_shipping_address = forms.BooleanField(required=False)
    save_info = forms.BooleanField(required=False)
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CartItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
