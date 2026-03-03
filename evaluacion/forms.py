from django import forms
from .models import Evaluacion, Emprendedora

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="Seleccionar archivo CSV")

class EmprendedoraAdminForm(forms.ModelForm):
    galeria_imagenes = forms.FileField(
        label="Añadir imágenes a la galería (selección múltiple)",
        widget=forms.FileInput(),  # Quitamos los atributos de aquí
        required=False,
        help_text="Puede seleccionar varias imágenes a la vez. Las imágenes existentes se pueden gestionar en la sección de abajo."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadimos el atributo 'multiple' después de la inicialización
        self.fields['galeria_imagenes'].widget.attrs.update({'multiple': True})

    class Meta:
        model = Emprendedora
        fields = '__all__'

class EvaluacionForm(forms.ModelForm):
    """
    Formulario para que el jurado ingrese las calificaciones de una emprendedora.
    """
    class Meta:
        model = Evaluacion
        # Campos que el jurado podrá rellenar.
        # 'jurado' y 'emprendedora' se asignarán en la vista.
        fields = [
            'score_coherencia',
            'score_trayectoria',
            'score_impacto',
            'score_creatividad',
            'score_viabilidad',
            'score_inversion',
            'score_presentacion',
            'score_pitch',
            'observaciones',
        ]
        # Aplicamos clases de Bootstrap 5 a los widgets del formulario
        widgets = {
            'score_coherencia': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_trayectoria': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_impacto': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_creatividad': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_viabilidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_inversion': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_presentacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'score_pitch': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Puntaje de 0 a 100'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }