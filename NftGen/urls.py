from django.urls import path,include
from NftGen.views import *

urlpatterns = [
    path('',loginView,name="login"),
    path('app/',LayerGet,name='LayerGet'),
    path('addproj/',add_proj,name='add_proj'),
    path('layoutP/',LayerPost,name='layoutP'),
    path('generate/',GenerateImg,name='GenerateImg'),
    path('download/',download,name='download'),
    path('uploadnft/',uploadnft,name='uploadnft'),
    path('editproj/<int:pk>',edit_proj,name='edit_proj'),
    path('upload/<int:pkk>',uploadImage,name='uploadImage'),
    path('setrarity/<int:k>',setrarity,name='setrarity'),

]
