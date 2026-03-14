from django.contrib import admin
from .models import UserProfile, Role


class UserProfileAdmin(admin.ModelAdmin):
    filter_horizontal = ("roles",)


admin.site.register(Role)
admin.site.register(UserProfile, UserProfileAdmin)
