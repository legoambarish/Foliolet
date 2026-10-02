from django.urls import path, include
from . import views

app_name='legacy'


urlpatterns = [
    path('', views.hub, name='index'),
    path('cases/', views.case_registry, name='case_registry'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cases/<str:case_id>/", views.case_detail, name="case_detail"),
    path("documents/", views.document_list, name="document_list"),
    path("documents/upload/", views.upload_document, name="upload_document"),
    path("documents/<str:document_id>/edit/", views.edit_document, name="edit_document"),
    path("documents/<str:document_id>/delete/", views.delete_document, name="delete_document"),
    path("audit-log/", views.audit_log, name="audit_log"),
    path("documents/<str:document_id>/verify/", views.verify_document, name="verify_document"),
    path("documents/<str:document_id>/analysis/", views.ai_document_analysis, name="ai_document_analysis"),
]