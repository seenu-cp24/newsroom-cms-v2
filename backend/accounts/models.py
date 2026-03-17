from django.db import models
from django.contrib.auth.models import User
from news.models import Edition

class Role(models.Model):

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    roles = models.ManyToManyField(
        Role,
        blank=True
    )

    edition = models.ForeignKey(
        Edition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    must_change_password = models.BooleanField(default=True)

    # -------------------------
    # ROLE HELPER FUNCTIONS
    # -------------------------

    def has_role(self, role_name):
        """
        Check if the user has a specific role
        Example: profile.has_role("editor")
        """
        return self.roles.filter(name__iexact=role_name).exists()

    def get_roles(self):
        """
        Return all role names as list
        Example: ['Reporter','SubEditor']
        """
        return [r.name for r in self.roles.all()]

    # -------------------------
    # DISPLAY IN ADMIN
    # -------------------------

    def __str__(self):

        roles = ", ".join(self.get_roles())

        return f"{self.user.username} ({roles})"


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:

        profile = UserProfile.objects.create(
            user=instance
        )

        # Assign default role
        try:
            default_role = Role.objects.get(name="Reporter")
            profile.roles.add(default_role)
        except:
            pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):

    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
