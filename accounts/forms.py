from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class AdminAccountCreationForm(forms.Form):
    """
    Form restricted to System Administrators for onboarding
    Warehouse Coordinator and Shelter Manager accounts.
    Explicitly prohibits granting admin, is_staff, or is_superuser flags.
    """
    ALLOWED_ROLES = [
        (User.Role.COORDINATOR, "Warehouse Coordinator"),
        (User.Role.SHELTER_MANAGER, "Shelter Manager"),
        (User.Role.VOLUNTEER, "Volunteer"),
    ]

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter unique username"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "operator@crisisnet.org"}),
    )
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(
        choices=ALLOWED_ROLES,
        initial=User.Role.COORDINATOR,
        help_text="Select operational role. Administrators cannot be created from this form.",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Initial secure password"}),
        help_text="Must meet standard password complexity criteria.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Re-type password"}),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_role(self):
        role = self.cleaned_data.get("role")
        allowed_values = [r[0] for r in self.ALLOWED_ROLES]
        if role not in allowed_values:
            raise ValidationError("Invalid role selected. Privileged roles cannot be created here.")
        return role

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                # Apply Django's built-in password validators
                temp_user = User(
                    username=cleaned_data.get("username", ""),
                    email=cleaned_data.get("email", ""),
                )
                try:
                    validate_password(password, user=temp_user)
                except ValidationError as e:
                    self.add_error("password", e)

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        user = User.objects.create_user(
            username=cleaned_data["username"],
            email=cleaned_data["email"],
            password=cleaned_data["password"],
            first_name=cleaned_data.get("first_name", ""),
            last_name=cleaned_data.get("last_name", ""),
            role=cleaned_data["role"],
        )
        # Enforce security constraints
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        return user
