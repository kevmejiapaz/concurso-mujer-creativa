from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Avg
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .models import Emprendedora, Evaluacion
from .forms import EvaluacionForm


def jurado_required(function):
    """
    Decorador para verificar que el usuario pertenece al grupo 'Jurado'.
    """
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Jurado').exists():
            return function(request, *args, **kwargs)
        else:
            messages.error(request, "No tienes permisos para acceder a esta página.")
            return redirect(reverse_lazy('login')) 
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap


def admin_required(function):
    """
    Decorador para verificar que el usuario es superuser o pertenece al grupo 'Administrador'.
    """
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Administrador').exists():
            return function(request, *args, **kwargs)
        else:
            messages.error(request, "No tienes permisos de administrador para acceder a esta página.")
            return redirect(reverse_lazy('home'))
    return wrap


# Create your views here.
@login_required
def home(request):
    """
    Vista principal que actúa como un dispatcher, mostrando el dashboard
    correspondiente según el rol del usuario.
    """
    user = request.user
    if user.is_superuser or user.groups.filter(name='Administrador').exists():
        # Lógica para el dashboard del admin: Ranking general
        ranking = Emprendedora.objects.annotate(
            promedio_fase1=Avg('evaluaciones__score_fase1'),
            promedio_pitch=Avg('evaluaciones__score_pitch'),
            promedio_total=Avg('evaluaciones__total_score')
        ).filter(promedio_total__isnull=False).order_by('-promedio_total')
        
        context = {'ranking': ranking}
        return render(request, 'evaluacion/dashboard_admin.html', context)

    elif user.groups.filter(name='Jurado').exists():
        # Lógica para el dashboard del jurado: Pendientes y evaluadas
        evaluaciones_hechas_ids = Evaluacion.objects.filter(jurado=user).values_list('emprendedora_id', flat=True)
        
        pendientes_list = Emprendedora.objects.exclude(id__in=evaluaciones_hechas_ids).order_by('nombre_completo')
        evaluadas_list = Emprendedora.objects.filter(id__in=evaluaciones_hechas_ids).order_by('-evaluaciones__fecha_evaluacion')

        # Paginación para pendientes (ajusta el número aquí)
        paginator_pendientes = Paginator(pendientes_list, 10)
        page_number_pendientes = request.GET.get('page_pendientes')
        pendientes_page_obj = paginator_pendientes.get_page(page_number_pendientes)

        # Paginación para evaluadas (ajusta el número aquí)
        paginator_evaluadas = Paginator(evaluadas_list, 10)
        page_number_evaluadas = request.GET.get('page_evaluadas')
        evaluadas_page_obj = paginator_evaluadas.get_page(page_number_evaluadas)

        context = {
            'pendientes': pendientes_page_obj,
            'evaluadas': evaluadas_page_obj,
        }
        return render(request, 'evaluacion/dashboard_jurado.html', context)
    
    else:
        # Usuario autenticado pero sin grupo asignado
        messages.info(request, "No tienes un rol asignado. Contacta al administrador.")
        return redirect(reverse_lazy('login'))


@login_required
@admin_required
def dashboard_admin_detalle(request):
    """
    Muestra una matriz de auditoría con el estado de evaluación de cada
    emprendedora por cada jurado.
    """
    jurados = User.objects.filter(groups__name='Jurado').order_by('username')
    emprendedoras = Emprendedora.objects.all().prefetch_related('evaluaciones__jurado')

    audit_data = []
    for emprendedora in emprendedoras:
        # Un diccionario para mapear jurado_id -> Scores (Fase 1, Pitch, Total)
        evaluaciones_hechas = {
            ev.jurado.id: {
                'f1': ev.score_fase1,
                'p': ev.score_pitch,
                't': ev.total_score
            } for ev in emprendedora.evaluaciones.all()
        }
        
        status_row = {
            'emprendedora': emprendedora,
            'status_por_jurado': []
        }
        for jurado in jurados:
            scores = evaluaciones_hechas.get(jurado.id)
            status_row['status_por_jurado'].append(scores) # Appends dict or None
        
        audit_data.append(status_row)

    context = {
        'jurados': jurados,
        'audit_data': audit_data,
    }
    return render(request, 'evaluacion/dashboard_admin_detalle.html', context)

@login_required
@jurado_required
def votar_emprendedora(request, emprendedora_id):
    emprendedora = get_object_or_404(Emprendedora, pk=emprendedora_id)
    
    # 1. Verificar si el jurado ya evaluó a esta emprendedora para poder editar.
    evaluacion_existente = Evaluacion.objects.filter(jurado=request.user, emprendedora=emprendedora).first()

    # 2. Procesar el formulario si es una petición POST
    if request.method == 'POST':
        # Si la evaluación existe, la pasamos como instancia para que se actualice.
        form = EvaluacionForm(request.POST, instance=evaluacion_existente)
        if form.is_valid():
            evaluacion = form.save(commit=False)
            evaluacion.jurado = request.user
            evaluacion.emprendedora = emprendedora
            evaluacion.save() # Aquí se ejecuta el método save() del modelo y se calcula el total
            
            if evaluacion_existente:
                messages.success(request, f"Has actualizado tu evaluación para {emprendedora.nombre_completo}.")
            else:
                messages.success(request, f"Has evaluado a {emprendedora.nombre_completo} exitosamente.")

            return redirect('home')
    else:
        # 3. Si es GET, mostrar el formulario. Si existe una evaluación, se pre-rellenará.
        form = EvaluacionForm(instance=evaluacion_existente)

    context = {
        'form': form,
        'emprendedora': emprendedora
    }
    return render(request, 'evaluacion/votar.html', context)
