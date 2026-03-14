from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from accounts.models import UserProfile

def user_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)

            # Get profile
            profile = user.userprofile

            # Force password change first login
            if profile.must_change_password:
                return redirect("/change-password/")

            # Multi-role redirect priority
            if profile.has_role("Editor"):
                return redirect("/editor-dashboard/")

            if profile.has_role("SubEditor"):
                return redirect("/subeditor-dashboard/")

            if profile.has_role("Reporter"):
                return redirect("/reporter-dashboard/")

            if profile.has_role("Paginator"):
                return redirect("/pagination-dashboard/")

            return redirect("/")

        else:
            messages.error(request, "Invalid username or password")

    return render(request, "accounts/login.html")



def user_logout(request):

    logout(request)

    return redirect('/login/')
