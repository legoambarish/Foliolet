from django.urls import path
from dashboard import bridge_views as views
urlpatterns = [
    path('health/', views.health),
    path('share/<str:token>/', views.share),
    path('share/<str:token>/open/', views.release),
    path('share/<str:token>/status/', views.share_status),
    path('verify/', views.public_verifier),
    path('discover/', views.discovery),
    path('imports/callback/', views.import_callback),
]
