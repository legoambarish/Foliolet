from django.urls import path, include
from django.conf import settings
from . import wallet_views as views
from . import foli_views as foli
from . import intake_views as intake
app_name = 'dashboard'
urlpatterns = [
 path('intake/pair/', intake.pair, name='intake-pair'),
 path('intake/sessions/', intake.sessions, name='intake-sessions'),
 path('intake/sessions/<uuid:session_id>/stop/', intake.stop, name='intake-stop'),
 path('intake/documents/<str:credential_id>/', intake.analysis, name='intake-analysis'),
 path('intake/documents/<str:credential_id>/retry/', intake.retry, name='intake-retry'),
 path('', views.home, name='index'),
 path('login/', views.login, name='login'),
 path('register/', views.register, name='register'),
 path('logout/', views.logout, name='logout'),
 path('ask-foli/', foli.home, name='foli'),
 path('ask-foli/api/documents/', foli.documents, name='foli-documents'),
 path('ask-foli/api/health/', foli.health, name='foli-health'),
 path('ask-foli/api/jobs/', foli.jobs, name='foli-jobs'),
 path('ask-foli/api/jobs/<uuid:job_id>/', foli.job, name='foli-job'),
 path('ask-foli/api/memory/', foli.memory, name='foli-memory'),
 path('ask-foli/api/source/', foli.source, name='foli-source'),
 path('ask-foli/api/page/', foli.source, {'image': True}, name='foli-page'),
 path('wallet/enroll/', views.enroll, name='enroll'),
 path('wallet/<str:credential_id>/', views.detail, name='detail'),
 path('wallet/<str:credential_id>/share/', views.compose, name='compose'),
 path('wallet/<str:credential_id>/file/', views.original, name='original'),
 path('wallet/<str:credential_id>/scan/', views.scan_fields, name='scan_fields'),
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
