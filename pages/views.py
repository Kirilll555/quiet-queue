from django.shortcuts import render

def index(request):
    return render(request, 'pages/index.html')

def rate_queue(request):
    return render(request, 'pages/rate.html')

def suggest_institution(request):
    return render(request, 'pages/suggest.html')

def ai_prediction(request):
    ai_response = "ИИ проанализировал данные. Лучшее время для визита — завтра с утра."
    return render(request, 'pages/prediction.html', {'ai_text': ai_response})