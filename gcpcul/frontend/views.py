from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'index.html')

def products(request):
    return render(request, 'products.html')

def about(request):
    return render(request, 'about.html')

def calculator(request): 
    return render(request, 'calculator.html')

def gallery(request):
    return render(request, 'gallery.html')

def downloads(request):
    return render(request, 'downloads.html')

def news(request):
    return render(request, 'news.html')

def login(request):
    return render(request, 'login.html')

def contact(request):
    return render(request, 'contact.html')
