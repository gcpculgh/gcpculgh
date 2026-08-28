from django.urls import path

from users import views

urlpatterns = [
    path("apply-for-loan/", views.loan_application, name="loan_application"),
    path('my-dashboard/', views.member_dashboard, name="members_dashboard")
]