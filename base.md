# DOCUMENTO TÉCNICO: Sistema de Evaluación "Mujer Creativa 2026"

## 1. Descripción del Proyecto

Sistema web monolítico desarrollado en **Django 5.x** utilizando **Django Templates** (sin frameworks SPA) para la gestión del proceso de evaluación del "Concurso Mujer Creativa y Emprendedora 2026". El sistema permitirá a los administradores registrar postulantes y a los jurados calificar bajo una matriz de 7 criterios ponderados.

## 2. Stack Tecnológico

* **Backend:** Python 3.10+ / Django 5.0+
* **Base de Datos:** PostgreSQL (recomendado) o SQLite (para desarrollo).
* **Frontend:** HTML5 + Jinja2 (Django Templates).
* **Estilos:** Bootstrap 5 (para prototipado rápido y responsividad).
* **Autenticación:** Sistema nativo de Django (`django.contrib.auth`).

## 3. Modelo de Datos (Database Schema)

La IA debe generar los `models.py` basándose en esta estructura para cumplir con las bases del concurso.

### A. Modelo: `Categoria`

Define las tres vertientes del concurso.
*
`nombre`: CharField. **Recomendación:** Usar `models.TextChoices` para definir las opciones de forma centralizada y segura en el modelo.
* `descripcion`: TextField.

### B. Modelo: `Emprendedora` (Candidata)

Almacena la información del formulario de inscripción y la carta de interés.
* `nombre_completo`: CharField.
* `nombre_emprendimiento`: CharField.
* `categoria`: ForeignKey (Modelo Categoria).
* `departamento`: CharField (Ubicación geográfica). **Recomendación:** Usar `models.TextChoices` para estandarizar los departamentos.
* `telefono`: CharField.
* `carta_interes`: TextField (Aquí va el texto vital para la evaluación).
* `anios_funcionamiento`: IntegerField (Debe ser > 1 año). **Recomendación:** Aplicar un `MinValueValidator(2)` en el modelo para forzar esta regla.
*
`empleos_generados`: CharField (Ej: "Directos: 3, Indirectos: 5"). Reemplaza al campo booleano `genera_empleo` para capturar más detalle.
* `descripcion_negocio`: TextField (Resumen del emprendimiento).
* `foto_producto`: ImageField (Opcional, referencia visual).

### C. Modelo: `Evaluacion`

Tabla transaccional donde el jurado emite sus votos. Debe tener una restricción `unique_together = ('jurado', 'emprendedora')`.
* `jurado`: ForeignKey (User - auth.User).
* `emprendedora`: ForeignKey (Modelo Emprendedora).
* `fecha_evaluacion`: DateTimeField (auto_now_add=True).
* **Criterios de Calificación:**
1. `score_coherencia`: Integer (Max 10 pts) - Coherencia con la categoría.
2. `score_trayectoria`: Integer (Max 15 pts) - Trayectoria y liderazgo.
3. `score_impacto`: Integer (Max 15 pts) - Impacto en el entorno/empleo.
4. `score_creatividad`: Integer (Max 15 pts) - Nivel de innovación/creatividad.
5. `score_viabilidad`: Integer (Max 15 pts) - Proyección y estabilidad.
6. `score_inversion`: Integer (Max 20 pts) - Intención de uso del premio (C$31,100).
7. `score_presentacion`: Integer (Max 10 pts) - Claridad en Carta/Pitch.
* `observaciones`: TextField (Opcional, para feedback de mentorías futuras).
* `total_score`: IntegerField. **Recomendación:** Definir con `editable=False` y calcularlo en el método `save()` del modelo para asegurar su integridad.

## 4. Lógica de Negocio y Vistas (Views)

### A. Roles de Usuario

1. **Administrador:** Puede Crear/Editar/Borrar Emprendedoras y ver el reporte final.
2. **Jurado:** Solo puede ver la lista de emprendedoras asignadas y acceder al formulario de evaluación. No puede editar datos de la emprendedora.

**Recomendación de Implementación:** Utilizar el sistema de Grupos de Django (`django.contrib.auth.models.Group`) para gestionar estos roles y proteger las vistas con decoradores o mixins.

### B. Vistas Requeridas (`views.py`)

1. **Dashboard (Home):**
* Si es Admin: Muestra tabla con Ranking total. **Recomendación técnica:** Se generará con una consulta `annotate` y `Avg` sobre el `total_score` de las evaluaciones.
* Si es Jurado: Muestra lista de emprendedoras pendientes de evaluar y evaluadas.

2. **Detalle de Emprendedora:**
* Muestra toda la info: Historia, Carta de Interés, Fotos.


3. **Formulario de Evaluación:**
* Uso de `forms.ModelForm`.
* Validación: Que los puntajes no excedan los máximos definidos (ej. no poner 20 en Coherencia).
* Cálculo automático del total antes de guardar.


4. **Reporte de Ganadoras:**
* Vista filtrada por Categoría.
* Ordenada por `total_score` descendente.
* Debe resaltar las 3 finalistas por categoría.





## 5. Diseño de Plantillas (Templates)

Estructura de carpetas sugerida para `templates/`:

* `base.html`: Navbar (logos institucionales: Nicaragua Creativa, Gobierno, China), Footer.
* `registration/login.html`: Formulario de acceso simple.
* `evaluacion/dashboard.html`: Tabla de candidatos.
* `evaluacion/votar.html`:
* **Columna Izquierda:** Información de la candidata (Sticky/Fija para leer mientras se califica).
* **Columna Derecha:** Formulario con los 7 campos de puntaje.

* `evaluacion/resultados.html`: Tabla de posiciones.

**Recomendación de Implementación:** Utilizar herencia de plantillas (`{% extends 'base.html' %}`) e `includes` (`{% include 'partials/navbar.html' %}`) para mantener el código DRY (Don't Repeat Yourself).

## 6. Instrucciones para la IA (Prompt Sugerido)

*Copia y pega esto en tu chat con la IA de programación:*

> "Actúa como un Desarrollador Senior de Python/Django. Necesito crear un sistema de evaluación para un concurso.
> **Contexto:** El sistema usará Django puro con templates (sin React). Usaremos Bootstrap 5 para el frontend.
> **Requerimiento 1:** Genera el archivo `models.py` con las siguientes especificaciones:
> * Modelo `Categoria` usando `models.TextChoices` para el campo `nombre` con las opciones: "Mujer Creativa y Cultural", "Mujer Emprendedora y Líder", "Mujer Innovadora".
> * Modelo `Emprendedora` con campos para nombre, descripción, `empleos_generados` (CharField), y un campo `anios_funcionamiento` con un `MinValueValidator(2)`.
> * Modelo `Evaluacion` que vincule un `User` (jurado) con una `Emprendedora`.
> * La `Evaluacion` debe tener exactamente estos 7 campos de enteros con sus validadores de Máximo Valor (`MaxValueValidator`):
>   1. Coherencia (Max 10)
>   2. Trayectoria (Max 15)
>   3. Impacto (Max 15)
>   4. Creatividad (Max 15)
>   5. Viabilidad (Max 15)
>   6. Inversión (Max 20)
>   7. Presentación (Max 10)
> * Incluye un método `save` en el modelo `Evaluacion` que sume automáticamente los 7 criterios en un campo `total_score`. Este campo `total_score` debe tener `editable=False`.
> **Requerimiento 2:** Genera un `forms.py` que use `ModelForm` para la evaluación, asegurando que los inputs tengan clases de Bootstrap.
> **Requerimiento 3:** Genera una vista basada en funciones (FBV) llamada `votar_emprendedora` que use el formulario anterior y asegure que un jurado no pueda votar dos veces a la misma persona."