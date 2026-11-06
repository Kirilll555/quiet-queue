from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('rate/', views.rate_queue, name='rate'),
    path('suggest/', views.suggest_institution, name='suggest'),
    path('ai-prediction/', views.ai_prediction, name='ai_prediction'),
]