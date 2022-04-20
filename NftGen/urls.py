from django.urls import path,include
from NftGen.views import *

urlpatterns = [
    path('',loginView,name="login"),
    path('home/',Home,name="home")
]
