from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.db import transaction
import csv
import re
import io

from .models import Categoria, Emprendedora, Evaluacion, FotoProducto
from .forms import CSVImportForm, EmprendedoraAdminForm


class FotoProductoInline(admin.TabularInline):
    model = FotoProducto
    extra = 0
    fields = ('display_imagen', 'imagen', 'descripcion')
    readonly_fields = ('display_imagen',)
    verbose_name = "Foto de Producto"
    verbose_name_plural = "Galería de Productos"

    def display_imagen(self, obj):
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return format_html('<img src="{}" width="100" />', obj.imagen.url)
        return "N/A"
    display_imagen.short_description = 'Vista Previa'
# Register your models here.

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Categoria.
    """
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Emprendedora)
class EmprendedoraAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Emprendedora.
    Mejora la visualización y la usabilidad.
    """
    change_list_template = "admin/evaluacion/emprendedora/change_list.html"
    list_display = ('nombre_completo', 'email', 'numero_cedula', 'nombre_emprendimiento', 'categoria', 'requiere_revision')
    list_filter = ('requiere_revision', 'categoria', 'departamento')
    search_fields = ('nombre_completo', 'nombre_emprendimiento', 'email')
    readonly_fields = ('display_foto_perfil',)
    inlines = [FotoProductoInline] # Mantenemos el inline para gestionar fotos existentes
    form = EmprendedoraAdminForm

    fieldsets = (
        ('Información Personal y de Contacto', {
            'fields': ('nombre_completo', 'email', 'numero_cedula', 'telefono', 'direccion', 'departamento')
        }),
        ('Información del Emprendimiento', {
            'fields': (
                'nombre_emprendimiento', 'categoria', 'descripcion_negocio',
                'anios_funcionamiento', 'empleos_generados', 'carta_interes'
            )
        }),
        ('Multimedia', {
            'fields': ('foto_perfil', 'display_foto_perfil', 'url_foto_cedula', 'galeria_imagenes')
        }),
        ('Estado de Revisión (Interno)', {
            'classes': ('collapse',),
            'fields': ('requiere_revision', 'revision_motivo')
        }),
    )

    def display_foto_perfil(self, obj):
        if obj.foto_perfil:
            return format_html('<img src="{}" width="150" />', obj.foto_perfil.url)
        return "No hay foto de perfil."
    display_foto_perfil.short_description = 'Vista Previa de Perfil'

    def save_related(self, request, form, formsets, change):
        """
        Sobrescribimos este método para manejar la carga de múltiples imágenes
        después de que el objeto principal y los inlines se hayan guardado.
        """
        super().save_related(request, form, formsets, change)
        
        files = request.FILES.getlist('galeria_imagenes')
        if files:
            for f in files:
                FotoProducto.objects.create(emprendedora=form.instance, imagen=f)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv, name='import_csv'),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]
                
                if not csv_file.name.endswith('.csv'):
                    self.message_user(request, "El archivo no es un CSV.", level='error')
                    return redirect(".")

                decoded_file = io.TextIOWrapper(csv_file.file, 'utf-8')
                reader = csv.DictReader(decoded_file)

                # Mapeos
                DEPARTAMENTO_MAP = {v: k for k, v in Emprendedora.Departamento.choices}
                try:
                    CATEGORIAS_MAP = {cat.get_nombre_display(): cat for cat in Categoria.objects.all()}
                    if len(CATEGORIAS_MAP) < len(Categoria.Nombre.choices):
                        for code, name in Categoria.Nombre.choices:
                            Categoria.objects.get_or_create(nombre=code, defaults={'descripcion': name})
                        CATEGORIAS_MAP = {cat.get_nombre_display(): cat for cat in Categoria.objects.all()}
                except Exception as e:
                    self.message_user(request, f"Error crítico al cargar categorías: {e}", level='error')
                    return redirect(".")

                registros_creados = 0
                registros_actualizados = 0
                registros_con_revision = 0
                errores = []

                try:
                    with transaction.atomic():
                        for i, row in enumerate(reader, 1):
                            # --- 1. Limpieza y Validación ---
                            requiere_revision_local = False
                            revision_motivo_local = ""
                            anios_str = row.get('Años de Operar', '0').lower()
                            anios_num = 0
                            numeros = re.findall(r'\d+\.?\d*', anios_str)
                            if numeros:
                                anios_num = float(numeros[0])
                                if 'meses' in anios_str: anios_num = anios_num / 12
                            
                            if anios_num < 2:
                                requiere_revision_local = True
                                revision_motivo_local = f"Antigüedad menor a 2 años ({anios_str})."

                            # --- 2. Mapeo de campos ---
                            categoria_obj = CATEGORIAS_MAP.get(row.get('Categoría'))
                            departamento_code = DEPARTAMENTO_MAP.get(row.get('Municipio de origen'))
                            email = row.get('Dirección de correo electrónico', '').strip().lower()

                            if not email:
                                errores.append(f"Fila {i}: Omitida por no tener dirección de correo electrónico.")
                                continue
                            
                            # Verificación de duplicados de cédula antes de guardar
                            cedula = row.get('Número de Cédula', '').strip()
                            if cedula:
                                if Emprendedora.objects.filter(numero_cedula=cedula).exclude(email=email).exists():
                                    errores.append(f"Fila {i}: Cédula '{cedula}' ya está en uso por otro registro. Fila para '{email}' omitida por duplicado.")
                                    continue
                            else:
                                cedula = None # Asegura que se guarde como NULL si está vacía
                            
                            nombre_completo = row.get('Nombre Completo', '').strip()

                            if not all([categoria_obj, departamento_code, nombre_completo]):
                                errores.append(f"Fila {i}: Datos incompletos o no reconocidos para '{email}'.")
                                continue

                            # --- 3. Preparación de datos ---
                            carta_url = row.get('Carta de interés de participación', '').strip()
                            carta_texto = f"Enlace a documento: {carta_url}" if carta_url else "No se proporcionó carta."
                            empleos_csv = row.get('¿Su emprendimiento genera empleo?', 'No').strip().lower()
                            empleos_valor = '1' if empleos_csv == 'sí' else '0'

                            # --- 4. Creación o Actualización ---
                            obj, created = Emprendedora.objects.update_or_create( # Usamos email como identificador único
                                email=email,
                                defaults={
                                    'nombre_completo': nombre_completo,
                                    'numero_cedula': cedula,
                                    'direccion': row.get('Dirección de domicilio', ''),
                                    'url_foto_cedula': row.get('Adjuntar foto de Cédula de Identidad (Ambos lados)', ''),
                                    'nombre_emprendimiento': row.get('Nombre del Emprendimiento', 'N/A'),
                                    'categoria': categoria_obj, 'departamento': departamento_code,
                                    'telefono': row.get('Número telefónico', 'N/A'),
                                    'carta_interes': carta_texto, 'anios_funcionamiento': int(anios_num),
                                    'empleos_generados': empleos_valor,
                                    'descripcion_negocio': "Descripción no proporcionada en el formulario.",
                                    'requiere_revision': requiere_revision_local,
                                    'revision_motivo': revision_motivo_local,
                                }
                            )
                            if created: registros_creados += 1
                            else: registros_actualizados += 1
                            if requiere_revision_local: registros_con_revision += 1
                except Exception as e:
                    self.message_user(request, f"Error durante la transacción: {e}. No se guardó ningún registro.", level='error')
                    return redirect(".")

                self.message_user(request, f"Importación finalizada. Creados: {registros_creados}, Actualizados: {registros_actualizados}.", level='success')
                if registros_con_revision > 0: self.message_user(request, f"{registros_con_revision} registros fueron marcados para revisión.", level='warning')
                for error in errores: self.message_user(request, error, level='error')
                return redirect("..")

        form = CSVImportForm()
        return render(request, "admin/evaluacion/csv_form.html", {"form": form})


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Evaluacion.
    Facilita la revisión de las calificaciones.
    """
    list_display = ('emprendedora', 'jurado', 'total_score', 'fecha_evaluacion')
    list_filter = ('jurado', 'emprendedora__categoria')
    search_fields = ('emprendedora__nombre_completo', 'jurado__username')
    
    # Hacemos que los campos calculados y de fecha sean de solo lectura
    readonly_fields = ('total_score', 'fecha_evaluacion')

    # Esto es útil para que los jurados no puedan cambiar a quién están evaluando
    # una vez que se ha creado el registro.
    # def get_readonly_fields(self, request, obj=None):
    #     if obj: # Si el objeto ya existe
    #         return self.readonly_fields + ('jurado', 'emprendedora')
    #     return self.readonly_fields
