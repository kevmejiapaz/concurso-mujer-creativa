from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.

class Categoria(models.Model):
    """Define las tres vertientes del concurso."""
    class Nombre(models.TextChoices):
        CULTURAL = 'MC', 'Mujer Creativa y Cultural'
        LIDER = 'ME', 'Mujer Emprendedora y Líder'
        INNOVADORA = 'MI', 'Mujer Innovadora'

    nombre = models.CharField(
        max_length=2,
        choices=Nombre.choices,
        unique=True,
        verbose_name="Nombre de Categoría"
    )
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.get_nombre_display()


class Emprendedora(models.Model):
    """Almacena la información de la candidata."""
    # Lista de departamentos para estandarizar la entrada de datos
    class Departamento(models.TextChoices):
        BOACO = 'BO', 'Boaco'
        CARAZO = 'CA', 'Carazo'
        CHINANDEGA = 'CI', 'Chinandega'
        CHONTALES = 'CO', 'Chontales'
        ESTELI = 'ES', 'Estelí'
        GRANADA = 'GR', 'Granada'
        JINOTEGA = 'JI', 'Jinotega'
        LEON = 'LE', 'León'
        MADRIZ = 'MD', 'Madriz'
        MANAGUA = 'MN', 'Managua'
        MASAYA = 'MS', 'Masaya'
        MATAGALPA = 'MA', 'Matagalpa'
        NUEVA_SEGOVIA = 'NS', 'Nueva Segovia'
        RIVAS = 'RI', 'Rivas'
        RIO_SAN_JUAN = 'RS', 'Río San Juan'
        RACCN = 'AN', 'RACCN'
        RACCS = 'AS', 'RACCS'

    nombre_completo = models.CharField(max_length=255, verbose_name="Nombre Completo")
    nombre_emprendimiento = models.CharField(max_length=255, verbose_name="Nombre del Emprendimiento")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="Categoría")
    departamento = models.CharField(max_length=2, choices=Departamento.choices, verbose_name="Departamento")
    email = models.EmailField(unique=True, verbose_name="Correo Electrónico", help_text="Este campo se usa como identificador único.")
    direccion = models.TextField(blank=True, verbose_name="Dirección del Domicilio")
    numero_cedula = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Número de Cédula")
    url_foto_cedula = models.URLField(max_length=500, blank=True, verbose_name="URL Foto de Cédula")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    carta_interes = models.TextField(verbose_name="Carta de Interés")
    anios_funcionamiento = models.PositiveIntegerField(
        verbose_name="Años de Funcionamiento",
        validators=[MinValueValidator(2, message="Debe tener al menos 2 años de funcionamiento.")]
    )
    empleos_generados = models.CharField(
        max_length=100,
        verbose_name="Empleos Generados",
        help_text="Ej: Directos: 3, Indirectos: 5"
    )
    descripcion_negocio = models.TextField(verbose_name="Descripción del Negocio")
    foto_perfil = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True,
        verbose_name="Foto de Perfil"
    )
    # Nuevos campos para el control de calidad de la importación
    requiere_revision = models.BooleanField(default=False, verbose_name="Requiere Revisión")
    revision_motivo = models.CharField(max_length=255, blank=True, verbose_name="Motivo de Revisión")

    class Meta:
        verbose_name = "Emprendedora"
        verbose_name_plural = "Emprendedoras"
        ordering = ['nombre_completo']

    def __str__(self):
        return f"{self.nombre_completo} - {self.nombre_emprendimiento}"

    @property
    def get_carta_interes_url(self):
        """
        Extrae la URL de la carta de interés si está presente en el texto,
        de lo contrario devuelve None.
        """
        prefix = "Enlace a documento: "
        if self.carta_interes.startswith(prefix):
            return self.carta_interes[len(prefix):].strip()
        # Como fallback, si el campo contiene solo una URL
        if self.carta_interes.startswith("http"):
            return self.carta_interes.strip()
        return None


class FotoProducto(models.Model):
    """Almacena las fotos de la galería de productos de una emprendedora."""
    emprendedora = models.ForeignKey(Emprendedora, related_name='galeria_productos', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos_galeria/', verbose_name="Imagen del Producto")
    descripcion = models.CharField(max_length=255, blank=True, verbose_name="Descripción Corta")

    class Meta:
        verbose_name = "Foto de Producto"
        verbose_name_plural = "Galería de Productos"

    def __str__(self):
        return f"Foto para {self.emprendedora.nombre_emprendimiento}"


class Evaluacion(models.Model):
    """Tabla transaccional donde el jurado emite sus votos."""
    jurado = models.ForeignKey(User, on_delete=models.CASCADE, related_name="evaluaciones")
    emprendedora = models.ForeignKey(Emprendedora, on_delete=models.CASCADE, related_name="evaluaciones")
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)

    # Criterios de Calificación
    score_coherencia = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(10)], verbose_name="1. Coherencia con la Categoría")
    score_trayectoria = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(15)], verbose_name="2. Trayectoria y Liderazgo")
    score_impacto = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(15)], verbose_name="3. Impacto en el Entorno/Empleo")
    score_creatividad = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(15)], verbose_name="4. Nivel de Innovación/Creatividad")
    score_viabilidad = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(15)], verbose_name="5. Proyección y Estabilidad")
    score_inversion = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(20)], verbose_name="6. Intención de Uso del Premio")
    score_presentacion = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(10)], verbose_name="7. Claridad en Carta/Pitch")

    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones Adicionales")
    total_score = models.PositiveIntegerField(default=0, editable=False, verbose_name="Puntaje Total")

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        # Asegura que un jurado solo pueda evaluar a una emprendedora una vez.
        unique_together = ('jurado', 'emprendedora')

    def __str__(self):
        return f"Evaluación de {self.emprendedora.nombre_completo} por {self.jurado.username}"

    def save(self, *args, **kwargs):
        # Calcula el puntaje total antes de guardar
        self.total_score = (
            self.score_coherencia + self.score_trayectoria +
            self.score_impacto + self.score_creatividad +
            self.score_viabilidad + self.score_inversion +
            self.score_presentacion
        )
        super().save(*args, **kwargs)
