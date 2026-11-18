# Generador de Horarios CUCEI — Checkpoint 1

**Fecha:** 18/11/2026

### Equipo: Sort-Analitycs
* LOPEZ OLIVERA ALEJANDRO ESAU
* RAMIREZ PEREZ OSCAR EMILIANO
* RODRIGUEZ HERNANDEZ LUIS GIOVANNI
* RUIZ LOPEZ CARLOS AARON

---

## Problema

El Centro Universitario de Ciencias Exactas e Ingeniería (CUCEI) tiene numerosas matrículas en la institución y muchas materias que los estudiantes pueden agendar. Al ser también muchos estudiantes, se pueden generar dificultades para las inscripciones, como la disponibilidad de cupos y la posibilidad de agendar materias que se adapten bien a tus necesidades personales.

A la hora de agendar en **SIIAU** o en **LEO** se pueden generar algunos problemas si no agendas a primera hora, ya que lo que tenías planeado puede quedar sin cupos para estudiantes. Además, al querer agregar en otro horario las que no alcanzaste, se puede llegar a tener empalmes de horario y tiempos muertos; con todo esto se pierde demasiado tiempo al registrar cada horario de cada alumno, provocando que haya colapsos en las páginas de registro por demasiados alumnos intentando agendar.

---

## FODA

| Fortalezas | Oportunidades |
| :--- | :--- |
| • Uso de un algoritmo de Backtracking para poder explorar combinaciones sin empalmes.<br>• Interfaz web intuitiva.<br>• Datos extraídos directamente de SIIAU en tiempo real (Scraping). | • Interés de alumnos de herramientas que faciliten la inscripción de CUCEI.<br>• Posibilidad de escalar el sistema a otros centros universitarios de UDG.<br>• Implementación y optimizaciones futuras para poder hacer el sistema más rápido y eficiente para los usuarios. |

| Debilidades | Amenazas |
| :--- | :--- |
| • Dependencia de la estructura de SIIAU; si la página llegara a cambiar, el scraping puede fallar.<br>• No se puede automatizar la inscripción real (solo genera los horarios).<br>• El algoritmo tiene un límite de exploración (100,000) para poder tener una respuesta en tiempo real; en un caso extremo de agendar muchas materias el sistema puede no dar la solución de tener un buen horario. | • Posibles caídas del servidor de SIIAU durante los periodos de las inscripciones.<br>• Que otras personas desarrollen una solución similar para el registro. |

---

## Backlog Inicial

Nuestro backlog inicial cuenta con un total de **20 tareas**, distribuyendo las tareas de la manera más óptima y eficiente para la correcta realización de nuestro proyecto[cite: 7]:

| No. de tarea | Nombre de la tarea | Descripción de la tarea |
| :---: | :--- | :--- |
| **01** | **Analizar y preparar el backend existente**[cite: 7] | Revisar el código Python actual e identificar los módulos que se pueden reutilizar[cite: 7]. |
| **02** | **Mejorar la consulta de información de SIIAU**[cite: 7] | Obtener materias, NRC, grupos, profesores, horarios y cupos disponibles[cite: 7]. |
| **03** | **Implementar validación de materias**[cite: 7] | Validar las claves ingresadas por el estudiante y detectar materias inexistentes o sin oferta[cite: 7]. |
| **04** | **Desarrollar endpoints de consulta**[cite: 7] | Crear servicios API para consultar materias, grupos y sus respectivos horarios[cite: 7]. |
| **05** | **Estandarizar y preparar los datos académicos**[cite: 8] | Organizar la información obtenida en estructuras JSON para que pueda utilizarla el algoritmo y el frontend[cite: 8]. |
| **06** | **Diseñar la lógica del algoritmo generador**[cite: 8] | Establecer las reglas y condiciones necesarias para combinar los grupos de las materias seleccionadas[cite: 8]. |
| **07** | **Desarrollar la generación de combinaciones**[cite: 8] | Crear el algoritmo en Python para producir diferentes combinaciones de horarios[cite: 8]. |
| **08** | **Implementar detección de empalmes**[cite: 8] | Evitar que dos materias se encuentren programadas en el mismo día y horario[cite: 8]. |
| **09** | **Implementar filtros de disponibilidad**[cite: 8] | Considerar los días y horarios en los que el estudiante puede asistir a clases[cite: 8]. |
| **10** | **Implementar optimización y clasificación de horarios**[cite: 8] | Ordenar las combinaciones según criterios como menos horas libres, jornadas compactas y preferencias del estudiante[cite: 8]. |
| **11** | **Diseñar la estructura HTML de la página**[cite: 8] | Crear la estructura principal de la aplicación y sus diferentes secciones[cite: 8]. |
| **12** | **Desarrollar los estilos CSS**[cite: 8] | Diseñar una interfaz visual atractiva, organizada, responsiva y fácil de utilizar[cite: 8]. |
| **13** | **Crear el formulario de selección de materias**[cite: 8] | Permitir ingresar, agregar y eliminar las materias que el estudiante desea cursar[cite: 8]. |
| **14** | **Implementar las preferencias del estudiante**[cite: 9] | Crear controles para seleccionar días disponibles, horarios preferidos y profesores deseados o excluidos[cite: 9]. |
| **15** | **Desarrollar la visualización de horarios**[cite: 9] | Mostrar los horarios generados en un calendario semanal, incluyendo materias, profesores y horas[cite: 9]. |
| **16** | **Conectar el frontend con el backend**[cite: 9] | Implementar peticiones HTTP con JavaScript utilizando Fetch API para consumir los servicios Python[cite: 9]. |
| **17** | **Integrar el algoritmo con la aplicación web**[cite: 9] | Conectar el formulario de materias y preferencias con el algoritmo generador de horarios[cite: 9]. |
| **18** | **Realizar pruebas funcionales**[cite: 9] | Verificar que las consultas, filtros y generación de horarios funcionen correctamente[cite: 9]. |
| **19** | **Configurar el despliegue en Vercel**[cite: 9] | Configurar el repositorio, archivos de publicación, variables de entorno y despliegue del frontend[cite: 9]. |
| **20** | **Documentar y validar la versión final**[cite: 9] | Documentar la instalación, arquitectura, funcionamiento y realizar una prueba integral de la aplicación publicada[cite: 9]. |

---

## Algoritmo Funcional

El algoritmo base implementado en el archivo `api/index.py` es un **Backtracking** (Búsqueda con Vuelta Atrás).

### Función
1. Se reciben en la página las claves de las materias que el alumno quiere cursar.
2. El sistema consulta en SIIAU y obtiene las secciones de las materias.
3. Se filtran las secciones que no cumplen con los días y horarios disponibles.
4. Con una función recursiva se prueba una sección de la primera materia, luego una de la segunda, así sucesivamente.
5. Si en el camino se detecta un empalme de horario, se descarta esa combinación y se retrocede para probar otras opciones.
6. Al finalizar, las combinaciones válidas se ordenan con los horarios más compactos.

### Complejidad Aproximada
En el peor de los casos, la complejidad temporal del algoritmo es:

$$O(N^M)$$

Donde **$N$** es el número promedio de secciones por materia y **$M$** es el número de materias solicitadas. Debido a ese crecimiento que es exponencial, el algoritmo implementa un **límite de seguridad de 100,000 evaluaciones** para garantizar que la respuesta sea breve.
