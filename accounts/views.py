from urllib.parse import urlencode
import requests

from django.conf import settings
from django.shortcuts import render, redirect
from django.views.generic import CreateView, FormView
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
import uuid
from datetime import timedelta
from .forms import RegisterForm, CustomLoginForm, ForgotPasswordForm, ResetPasswordForm
from .models import PasswordResetToken

User = get_user_model()


class RegisterView(CreateView):
    """User registration view."""
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "Please create/login using Skill Jobs.")
        return redirect("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response


class CustomLoginView(LoginView):
    """Custom login view matching site design."""
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()

        if getattr(user, "is_sso_user", False):
            messages.error(self.request, "Please login using Skill Jobs.")
            return redirect("accounts:login")

        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect users to the appropriate dashboard based on role."""
        user = getattr(self.request, 'user', None)
        # Fallback to student dashboard for anonymous or unexpected cases
        if not user or not user.is_authenticated:
            return reverse_lazy('dashboard:student_dashboard')

        # Admin / staff users -> admin dashboard
        if hasattr(user, 'is_admin_user') and user.is_admin_user():
            return reverse_lazy('dashboard:admin_dashboard')

        # Instructors -> instructor dashboard
        if getattr(user, 'role', '') == 'instructor' or (hasattr(user, 'is_instructor') and user.is_instructor()):
            return reverse_lazy('dashboard:instructor_dashboard')

        # Default -> student dashboard
        return reverse_lazy('dashboard:student_dashboard')


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


class ForgotPasswordView(FormView):
    """Forgot password view."""
    form_class = ForgotPasswordForm
    template_name = 'accounts/forgot-password.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.get(email=email)
        
        # Delete existing token if any
        PasswordResetToken.objects.filter(user=user).delete()
        
        # Create new token
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=24)
        
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        messages.success(self.request, 'Password reset link sent to your email.')
        return super().form_valid(form)


class ResetPasswordView(FormView):
    """Reset password with token view."""
    form_class = ResetPasswordForm
    template_name = 'accounts/reset-password.html'
    success_url = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.get('token')
        try:
            self.reset_token = PasswordResetToken.objects.get(
                token=self.token,
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            messages.error(request, 'Invalid or expired reset token.')
            return redirect('core:home')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        password = form.cleaned_data['password']
        user = self.reset_token.user
        user.set_password(password)
        user.save()
        
        # Mark token as used
        self.reset_token.is_used = True
        self.reset_token.save()
        
        messages.success(self.request, 'Password reset successfully. Please log in.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['token'] = self.token
        return context



def _absolute_callback_url(request):
    return request.build_absolute_uri(reverse_lazy("accounts:skilljobs_callback"))


def _role_from_skilljobs_payload(data):
    group = (data.get("group") or data.get("user_type") or data.get("role") or "").lower()

    if group in ["instructor", "teacher"]:
        return "instructor"

    if group in ["admin", "staff", "superuser"]:
        return "admin"

    return "student"


def _safe_username(data):
    username = data.get("username") or data.get("email")
    if not username:
        raise ValueError("Skill Jobs response has no username/email.")
    return username.strip()


def _sync_skilljobs_user(data):
    username = _safe_username(data)
    email = (data.get("email") or username).strip()
    role = _role_from_skilljobs_payload(data)

    defaults = {
        "email": email,
        "role": role,
        "is_verified": True,
        "is_active": True,
        "is_sso_user": True,
        "sso_provider": "skilljobs",
        "sso_last_synced_at": timezone.now(),
    }

    if data.get("id"):
        defaults["skilljobs_user_id"] = str(data.get("id"))

    if data.get("uuid"):
        defaults["skilljobs_uuid"] = str(data.get("uuid"))

    first_name = data.get("first_name") or data.get("firstName")
    last_name = data.get("last_name") or data.get("lastName")

    if first_name:
        defaults["first_name"] = first_name

    if last_name:
        defaults["last_name"] = last_name

    phone = data.get("phone") or data.get("mobile") or data.get("work_mobile")
    if phone:
        defaults["phone"] = str(phone)

    bio = data.get("bio") or data.get("objectives") or data.get("summary")
    if bio:
        defaults["bio"] = bio

    user, created = User.objects.update_or_create(
        username=username,
        defaults=defaults,
    )

    if created or user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])

    return user


def skilljobs_login_start(request):
    next_url = request.GET.get("next")
    if next_url:
        request.session["skilljobs_sso_next"] = next_url

    from_domain = request.get_host()
    return redirect(f"{settings.SKILLJOBS_BASE_URL}/sso?from={from_domain}")


def skilljobs_callback(request):
    code = request.GET.get("code")

    if not code:
        messages.error(request, "Skill Jobs login failed. Missing authorization code.")
        return redirect("accounts:login")

    callback_url = _absolute_callback_url(request)

    try:
        response = requests.post(
            settings.SKILLJOBS_SSO_EXCHANGE_URL,
            data={
                "code": code,
            },
            timeout=getattr(settings, "SKILLJOBS_SSO_TIMEOUT", 15),
        )
    except requests.RequestException:
        messages.error(request, "Could not connect to Skill Jobs. Please try again.")
        return redirect("accounts:login")

    if response.status_code != 200:
        messages.error(request, "Skill Jobs login verification failed.")
        return redirect("accounts:login")

    data = response.json()

    user_data = data.get("user") if isinstance(data.get("user"), dict) else data

    try:
        user = _sync_skilljobs_user(user_data)
    except Exception:
        messages.error(request, "Could not sync your Skill Jobs profile.")
        return redirect("accounts:login")

    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)

    messages.success(request, "Logged in successfully with Skill Jobs.")

    next_url = request.session.pop("skilljobs_sso_next", None)

    if next_url:
        return redirect(next_url)

    if user.is_admin_user():
        return redirect("dashboard:admin_dashboard")

    if user.is_instructor():
        return redirect("dashboard:instructor_dashboard")

    return redirect("dashboard:student_dashboard")


@login_required
def profile_view(request):
    """View user profile."""
    context = {'user': request.user}
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit user profile."""
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.phone = request.POST.get('phone')
        request.user.bio = request.POST.get('bio')
        
        if 'profile_image' in request.FILES:
            request.user.profile_image = request.FILES['profile_image']
        
        request.user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/edit-profile.html')
