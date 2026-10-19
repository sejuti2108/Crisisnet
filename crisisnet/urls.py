
from django.contrib import admin
from django.urls import path
from requests_app.views import live_test, test_broadcast
urlpatterns = [
    path('admin/', admin.site.urls),
     path("live/", live_test),
     path("test-broadcast/", test_broadcast),
]
