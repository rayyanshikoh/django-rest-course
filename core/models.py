from django.db import models
from django.contrib.auth.models import AbstractUser


# When extending the user model
class User(AbstractUser):
    email = models.EmailField(unique=True)
