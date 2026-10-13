from django.urls import path, include
from django.conf import settings
from . import wallet_views as views
from . import bridge_views as bridge
app_name = 'dashboard'
urlpatterns = [
 path('health/', bridge.health),
 path('bridge/', bridge.home, name='bridge'),
 path('bridge/assistant/stream/', bridge.assistant_stream),
 path('bridge/api/<path:operation>/', bridge.proxy),
 path('bridge/upload/', bridge.upload),
 path('share/<str:token>/', bridge.share),
 path('share/<str:token>/open/', bridge.release),
 path('share/<str:token>/status/', bridge.share_status),
 path('', views.home, name='index'),
 path('login/', views.login, name='login'),
 path('register/', views.register, name='register'),
 path('logout/', views.logout, name='logout'),
 path('wallet/enroll/', views.enroll, name='enroll'),
 path('wallet/<str:credential_id>/', views.detail, name='detail'),
 path('wallet/<str:credential_id>/share/', views.compose, name='compose'),
 path('wallet/<str:credential_id>/file/', views.original, name='original'),
 path('wallet/<str:credential_id>/<str:action>/', views.document_action, name='document_action'),
 path('versions/<str:previous_id>/', views.enroll, name='version'),
 path('sharing/', views.sharing, name='sharing'),
 path('sharing/<str:grant_id>/revoke/', views.revoke_share, name='revoke_share'),
 path('integrity/', views.integrity, name='integrity'),
 path('integrity/<str:agent_id>/revoke/', views.revoke_agent, name='revoke_agent'),
 path('verify/<str:token>/', views.verify, name='verify'),
 path('proof-status/<str:grant_id>/', views.proof_status, name='proof_status'),
 path('proof-download/<str:grant_id>/', views.proof_download, name='proof_download'),
]
if settings.ENABLE_LEGACY_UI:
 urlpatterns.append(path('legacy/', include('dashboard.legacy_urls', namespace='legacy')))
