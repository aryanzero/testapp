from django.urls import reverse_lazy
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, CreateView
from sneaksbid.models import Item, Bid, OrderItem
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from snekasbiddjangoProject import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import authenticate, login, logout
from .tokens import generate_token
from decimal import Decimal
from django.conf import settings
from .forms import SignUpForm, ShoeForm
from .forms import SignInForm, CheckoutForm
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PaymentForm, BidForm, Bid
from .models import Payment2, Shoe, Order, BillingAddress, Bid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from .models import Item
from django.db.models import F
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

'''class HomeView(ListView):
    template_name = "./sneaksbid/homepage.html"
    context_object_name = 'items'
    ordering = ['-bid_expiry']

    def get_queryset(self):
        return Item.objects.all()'''


class HomeView(ListView):
    template_name = "./sneaksbid/homepage.html"
    context_object_name = 'items'
    ordering = ['-bid_expiry']

    def get_queryset(self):
        return Item.objects.all()

    def dispatch(self, request, *args, **kwargs):
        # Initialize or increment the visit count in the session
        if 'visit_count' in request.session:
            request.session['visit_count'] += 1
        else:
            request.session['visit_count'] = 1

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Include visit count in the context
        context['visit_count'] = self.request.session['visit_count']
        return context

def user_history(request):
    # Retrieve the user's search history from the session
    search_history = request.session.get('search_history', [])
    
    # Retrieve the session count
    visit_count = request.session.get('visit_count', 0)
    
    context = {
        'visit_count': visit_count,
        'search_history': search_history,
    }
    return render(request, 'sneaksbid/user_history.html', context)

def signin(request):
    if request.method == 'POST':
        form = SignInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                fname = user.first_name
                # messages.success(request, "Logged In Successfully!!")
                return render(request, "authentication/index.html", {"fname": fname})
            else:
                messages.error(request, "Bad Credentials!!")
                return redirect('home')
    else:
        form = SignInForm()
    return render(request, "authentication/signin.html", {'form': form})


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password1 = form.cleaned_data.get('password1')
            password2 = form.cleaned_data.get('password2')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists! Please try some other username.")
                return redirect('home')

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email Already Registered!!")
                return redirect('home')

            if password1 != password2:
                messages.error(request, "Passwords didn't match!!")
                return redirect('home')

            user = form.save(commit=False)
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = False  # Change to `True` if you don't need email confirmation
            user.save()

            # Send welcome email
            subject = "Welcome to SneaksBid Login!!"
            message = "Hello " + user.first_name + "!! \n" + "Welcome to SneaksBid!! \nThank you for visiting our website.\nWe have also sent you a confirmation email, please confirm your email address.\n\nThanking You\n"
            from_email = settings.EMAIL_HOST_USER
            to_list = [user.email]
            send_mail(subject, message, from_email, to_list, fail_silently=True)

            # Send email confirmation
            current_site = get_current_site(request)
            email_subject = "Confirm your Email @ SneaksBid Login!!"
            message2 = render_to_string('email_confirmation.html', {
                'name': user.first_name,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': generate_token.make_token(user)
            })
            email = EmailMessage(
                email_subject,
                message2,
                settings.EMAIL_HOST_USER,
                [user.email],
            )
            email.fail_silently = True
            email.send()

            messages.success(request,
                             "Your Account has been created successfully! Please check your email to confirm your email address in order to activate your account.")
            return redirect('signin')
        else:
            # Form is not valid
            messages.error(request, "Error processing your form.")
    else:
        form = SignUpForm()
    return render(request, 'authentication/signup.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        myuser = None

    if myuser is not None and generate_token.check_token(myuser, token):
        myuser.is_active = True
        # user.profile.signup_confirmation = True
        myuser.save()
        login(request, myuser)
        messages.success(request, "Your Account has been activated!!")
        return redirect('signin')
    else:
        return render(request, 'activation_failed.html')


def signout(request):
    logout(request)
    messages.success(request, "Logged Out Successfully!!")
    return redirect('home')


def shop(request):
    # Retrieve all items from the database
    sneakers = Item.objects.all()

    context = {
        'sneakers': sneakers,
    }

    return render(request, 'sneaksbid/shop.html', context)


def search_sneakers(request):
    query = request.GET.get('query')
    search_results = Item.objects.filter(title__icontains=query)

    # Retrieve the user's search history from the session
    search_history = request.session.get('search_history', [])
    # Add the current search query to the search history
    search_history.append(query)
    # Update the search history in the session
    request.session['search_history'] = search_history
    
    return render(request, 'sneaksbid/search_result.html', {'search_results': search_results})


def item_detail(request, item_id):
    # Your existing code to get the item
    item = get_object_or_404(Item, pk=item_id)
    is_auction_active = item.is_auction_active
    winning_bid = item.bids.filter(is_winner=True).first()
    last_10_bids = item.bids.all().order_by('-bid_time')[:10]
    # Pass 'winning_bid' to the template context
    context = {
        'item': item,
        'is_auction_active': is_auction_active,
        'winning_bid': winning_bid,
        'last_10_bids': last_10_bids,
        # ... other context variables ...
    }

    return render(request, 'sneaksbid/item_detail.html', context)


@login_required
def place_bid(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if not item.available:
        messages.error(request, "The item is not available.")
        return redirect('item_detail', item_id=item.id)

    user_won_auction = False

    if request.method == 'POST':
        form = BidForm(request.POST, item=item)
        if form.is_valid():
            bid_amount = form.cleaned_data['bid_amount']
            last_bid = item.bids.order_by('-bid_amount').first()
            if last_bid and bid_amount <= last_bid.bid_amount:
                messages.error(request, "Your bid must be higher than the current highest bid.")
                return redirect('place_bid', item_id=item.id)
            elif bid_amount <= item.base_price:
                messages.error(request, "Your bid must be higher than the base price.")
                return redirect('place_bid', item_id=item.id)

            bid = form.save(commit=False)
            bid.item = item
            bid.user = request.user
            bid.save()

            # Update previous winning bid
            previous_winner = item.bids.filter(is_winner=True).first()
            if previous_winner:
                previous_winner.is_winner = False
                previous_winner.save()

            # Update the winning bid
            bid.is_winner = True
            bid.save()

            messages.success(request, "Bid placed successfully.")

            # Check if the current user won the auction
            user_won_auction = item.bids.filter(is_winner=True, user=request.user).exists()

            return redirect('item_detail', item_id=item.id)
        else:
            messages.error(request, "There was a problem with your bid.")
    else:
        form = BidForm(item=item)
    user = User.username
    context = {
        'form': form,
        'item': item,
        'user_won_auction': user_won_auction,
        'user': user,
    }

    return render(request, 'sneaksbid/bid.html', context)


class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        # Retrieve winning bid details for the current user
        form = CheckoutForm()
        winning_bids = Bid.objects.filter(user=request.user, is_winner=True)

        # Pass bid details to the template for rendering the checkout form
        context = {'form': form, 'winning_bids': winning_bids}
        return render(request, 'sneaksbid/checkout.html', context)

    def post(self, request, *args, **kwargs):
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Process the form data and save it to the database
            billing_address = BillingAddress(
                user=request.user,
                street_address=form.cleaned_data.get('street_address'),
                apartment_address=form.cleaned_data.get('apartment_address'),
                country=form.cleaned_data.get('country'),
                zip_code=form.cleaned_data.get('zip'),
                same_shipping_address=form.cleaned_data.get('same_shipping_address'),
                save_info=form.cleaned_data.get('save_info'),
                payment_option=form.cleaned_data.get('payment_option')
            )
            billing_address.save()

            # Redirect to a different URL upon successful checkout
            return HttpResponseRedirect(reverse('process_payment'))

        # If form is not valid, render the checkout form again with error messages
        context = {'form': form}
        return render(request, 'sneaksbid/checkout.html', context)


import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import PaymentForm

stripe.api_key = settings.STRIPE_SECRET_KEY

class ShoeCreateView(LoginRequiredMixin, CreateView):
    model = Shoe
    form_class = ShoeForm
    template_name = 'sneaksbid/shoe_form.html'  # Adjust the template path if needed
    success_url = reverse_lazy('home')
    login_url = '/signin/'



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import UserUpdateForm, ProfileImageForm


@login_required
def dashboard(request):
    if request.method == 'POST':
        #user_form = UserUpdateForm(request.POST, instance=request.user)
        image_form = ProfileImageForm(request.POST, request.FILES, instance=request.user.profile)
        password_form = PasswordChangeForm(request.user, request.POST)

        if 'update_profile' in request.POST:
            if image_form.is_valid():
                #user_form.save()
                image_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('dashboard')

        if 'change_password' in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request,
                                         user)  # Important for keeping the user logged in after password change
                messages.success(request, 'Your password was successfully updated!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the error below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        image_form = ProfileImageForm(instance=request.user.profile)
        password_form = PasswordChangeForm(request.user)

    context = {
        #'user_form': user_form,
        'image_form': image_form,
        'password_form': password_form
    }

    return render(request, 'sneaksbid/dashboard.html', context)



def add_to_cart(request, item_id):
    # Retrieve the item to be added to the cart
    item = get_object_or_404(Item, pk=item_id)

    # Retrieve or create the cart items list in the session
    cart_items = request.session.get('cart_items', [])

    # Check if the item is already in the cart
    # here we can alter the quantity or not bother at all
    for cart_item in cart_items:
        if cart_item['item_id'] == item_id:
            cart_item['quantity'] += 1
            break
    else:
        # If the item is not in the cart, add it
        cart_items.append({'item_id': item_id, 'quantity': 1})

    # Save the updated cart items list back to the session
    request.session['cart_items'] = cart_items

    return redirect('view_cart')


@login_required
def view_cart(request):
    cart_items = request.session.get('cart_items', [])
    items = []
    total_winning_bid = 0
    logged_in_user_name = request.user.username

    for cart_item in cart_items:
        item = get_object_or_404(Item, pk=cart_item['item_id'])
        winning_bid = item.bids.filter(is_winner=True).first()
        if winning_bid:
            total_winning_bid += winning_bid.bid_amount

        items.append({'item': item, 'quantity': cart_item['quantity'], 'winning_bid': winning_bid})

    # Store the total winning bid in the session
    request.session['total_winning_bid'] = float(total_winning_bid)

    context = {'items': items, 'total_winning_bid': total_winning_bid, 'logged_in_user_name': logged_in_user_name}
    return render(request, 'sneaksbid/cart.html', context)

@login_required
def process_payment(request):
    total_winning_bid = request.session.get('total_winning_bid', 0)

    if total_winning_bid == 0:
        messages.error(request, "You do not have any winning bids to pay for.")
        return redirect('home')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            token = request.POST.get('stripeToken')
            try:
                charge = stripe.Charge.create(
                    amount=int(total_winning_bid * 100),  # Convert dollars to cents
                    currency='usd',
                    source=token,
                )
                Payment2.objects.create(
                    user=request.user,
                    amount=total_winning_bid,
                    stripe_charge_id=charge.id,
                )
                messages.success(request, 'Payment successful!')
                # No need to update the winning_bid since we are not using it anymore
                return redirect('payment_success')
            except stripe.error.StripeError:
                messages.error(request, 'Payment error!')
    else:
        form = PaymentForm()

    return render(request, 'sneaksbid/payment.html', {
        'form': form,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLIC_KEY,
        'total_winning_bid': total_winning_bid
    })
