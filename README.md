# Generador de Horarios SIIAU 🎓

Aplicación web para generar horarios óptimos en el CUCEI (UDG) sin empalmes, basada en las preferencias del estudiante.

##  Arquitectura del Backend (T01)

El backend está desarrollado en **Python con FastAPI** (`api/index.py`). Se encarga de procesar la información y se divide en los siguientes módulos:

1. **Scraping (`extraer_oferta_siiau`)**: Se conecta a la página de SIIAU para extraer materias, NRC, profesores, horarios y cupos disponibles.
2. **Estandarización de datos (T05)**: Clasifica las secciones en `status: "disponible"` o `"lleno"` y agrega el campo `tipo: "seccion"` para unificar el JSON que consume el frontend.
3. **Validación de Filtros (T09)**: Utiliza validadores de Pydantic (`field_validator`) para limpiar y asegurar que los días, horas y profesores lleguen en el formato correcto antes de procesarlos.
4. **Algoritmo Generador (`generar_combinaciones`)**: Realiza una búsqueda combinatoria (backtracking) para armar horarios sin empalmes, aplicando filtros de disponibilidad.
5. **Clasificación (`puntuar_horario`)**: Calcula la calidad del horario penalizando tiempos muertos (huecos) y premiando a los profesores deseados.

## 🔌 Endpoints principales
- `GET /api/oferta`: Consulta las secciones de una materia.
- `POST /api/materias/validar`: Revisa si las claves existen en la oferta.
- `POST /api/horarios/generar`: Genera los horarios finales sin empalmes.