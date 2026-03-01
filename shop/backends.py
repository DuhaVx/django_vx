from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        user = None
        if '@' in username:
            user = User.objects.filter(email=username).first()
        if user is None:
            user = User.objects.filter(username=username).first()
        if user and user.check_password(password):
            return user
        return None
