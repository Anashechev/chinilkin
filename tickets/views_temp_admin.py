from django.shortcuts import HttpResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

@csrf_exempt
def promote_to_admin(request):
    """
    Temporary view to promote first user to admin
    Access this view once to make the first registered user an admin
    """
    if request.method == 'GET':
        # Get first user
        first_user = User.objects.first()
        if first_user:
            first_user.role = 'admin'
            first_user.is_staff = True
            first_user.is_superuser = True
            first_user.save()
            return HttpResponse(f"User {first_user.username} promoted to admin successfully!")
        else:
            return HttpResponse("No users found. Register first at /register")
    return HttpResponse("Use GET request to promote first user")
