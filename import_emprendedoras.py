import csv
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from evaluacion.models import Emprendedora, Categoria

class Command(BaseCommand):
    help = 'Importa emprendedoras desde un archivo CSV de Google Forms.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='La ruta del archivo CSV a importar.')

    @transaction.atomic
    def handle(self, *args, **options):
        csv_filepath = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importación desde "{csv_filepath}"...'))

        # Mapeo de nombres en el CSV a los códigos en el modelo
        DEPARTAMENTO_MAP = {v: k for k, v in Emprendedora.Departamento.choices}
        
        # Pre-cargamos las categorías para eficiencia
        try:
            CATEGORIAS_MAP = {cat.get_nombre_display(): cat for cat in Categoria.objects.all()}
            if not CATEGORIAS_MAP:
                self.stdout.write(self.style.WARNING('No se encontraron categorías en la base de datos. Creándolas...'))
                for code, name in Categoria.Nombre.choices:
                    cat_obj, created = Categoria.objects.get_or_create(nombre=code, defaults={'descripcion': name})
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Categoría "{name}" creada.'))
                # Recargamos el mapa
                CATEGORIAS_MAP = {cat.get_nombre_display(): cat for cat in Categoria.objects.all()}

        except Exception as e:
            raise CommandError(f"Error al cargar o crear categorías: {e}")

        registros_creados = 0
        registros_actualizados = 0
        registros_omitidos = 0

        try:
            with open(csv_filepath, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader, 1):
                    # --- 1. Limpieza y Validación de Años de Operar ---
                    anios_str = row.get('Años de Operar', '0').lower()
                    anios_num = 0
                    numeros = re.findall(r'\d+\.?\d*', anios_str)
                    if numeros:
                        anios_num = float(numeros[0])
                        if 'meses' in anios_str:
                            anios_num = anios_num / 12
                    
                    if anios_num < 2:
                        self.stdout.write(self.style.WARNING(f"OMITIDO (Fila {i}): {row['Nombre Completo']} tiene menos de 2 años de operación ('{anios_str}')."))
                        registros_omitidos += 1
                        continue

                    # --- 2. Mapeo de Categoría y Departamento ---
                    categoria_nombre = row.get('Categoría')
                    categoria_obj = CATEGORIAS_MAP.get(categoria_nombre)
                    if not categoria_obj:
                        self.stdout.write(self.style.WARNING(f"OMITIDO (Fila {i}): Categoría '{categoria_nombre}' no reconocida para {row['Nombre Completo']}."))
                        registros_omitidos += 1
                        continue

                    departamento_nombre = row.get('Municipio de origen')
                    departamento_code = DEPARTAMENTO_MAP.get(departamento_nombre)
                    if not departamento_code:
                        self.stdout.write(self.style.WARNING(f"OMITIDO (Fila {i}): Departamento '{departamento_nombre}' no reconocido para {row['Nombre Completo']}."))
                        registros_omitidos += 1
                        continue

                    # --- 3. Preparación de datos para el modelo ---
                    nombre_completo = row.get('Nombre Completo', '').strip()
                    if not nombre_completo:
                        self.stdout.write(self.style.WARNING(f"OMITIDO (Fila {i}): Nombre completo está vacío."))
                        registros_omitidos += 1
                        continue

                    carta_interes_url = row.get('Carta de interés de participación', '').strip()
                    carta_texto = (
                        f"El texto de la carta de interés se encuentra en el siguiente enlace. "
                        f"Por favor, copie y pegue en su navegador para visualizarlo:\n\n{carta_interes_url}"
                        if carta_interes_url else "No se proporcionó carta de interés."
                    )

                    # --- 4. Creación o Actualización del Registro ---
                    obj, created = Emprendedora.objects.update_or_create(
                        nombre_completo=nombre_completo,
                        defaults={
                            'nombre_emprendimiento': row.get('Nombre del Emprendimiento', 'N/A'),
                            'categoria': categoria_obj,
                            'departamento': departamento_code,
                            'telefono': row.get('Número telefónico', 'N/A'),
                            'carta_interes': carta_texto,
                            'anios_funcionamiento': int(anios_num),
                            'empleos_generados': row.get('¿Su emprendimiento genera empleo?', 'No especificado'),
                            'descripcion_negocio': "Descripción no proporcionada en el formulario de inscripción.",
                        }
                    )

                    if created:
                        registros_creados += 1
                        self.stdout.write(self.style.SUCCESS(f"CREADO: {obj.nombre_completo}"))
                    else:
                        registros_actualizados += 1
                        self.stdout.write(f"ACTUALIZADO: {obj.nombre_completo}")

        except FileNotFoundError:
            raise CommandError(f'Archivo no encontrado en la ruta: "{csv_filepath}"')
        except Exception as e:
            raise CommandError(f'Ocurrió un error durante la importación: {e}')

        self.stdout.write(self.style.SUCCESS('\n--- Resumen de la Importación ---'))
        self.stdout.write(f"Registros creados: {registros_creados}")
        self.stdout.write(f"Registros actualizados: {registros_actualizados}")
        self.stdout.write(f"Registros omitidos: {registros_omitidos}")
        self.stdout.write(self.style.SUCCESS('¡Importación completada exitosamente!'))