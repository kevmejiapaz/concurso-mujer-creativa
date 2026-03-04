from django.urls import path
from . import views

app_name = 'evaluacion'

urlpatterns = [
    path('votar/<int:emprendedora_id>/', views.votar_emprendedora, name='votar'),
    path('dashboard/detalle/', views.dashboard_admin_detalle, name='dashboard_admin_detalle'),
    path('dashboard/finalistas/', views.dashboard_finalistas, name='dashboard_finalistas'),
]