from django.shortcuts import render

# Create your views here.
def member_dashboard(request):
    return render(request, "member_dashboard.html")

def loan_application(request):
    return render(request, 'loan_application.html')