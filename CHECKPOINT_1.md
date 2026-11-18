Equipo: Sort-Analitycs
LOPEZ OLIVERA ALEJANDRO ESAU 
RAMIREZ PEREZ OSCAR EMILIANO 
RODRIGUEZ HERNANDEZ LUIS GIOVANNI
RUIZ LOPEZ CARLOS AARON

CHECKPOINT 1

Fecha: 18/11/2026


Problema:
El Centro Universitario de Ciencias Exactas e Ingeniería (CUCEI) tiene numerosas matrículas en la institución, muchas materias que los estudiantes pueden agendar. Al ser también muchos estudiantes, se pueden generar dificultades para las inscripciones, como la disponibilidad de cupos y la posibilidad de agendar materias que se adapten bien a tus necesidades personales.
A la hora de agendar en SIIAU o en LEO puede generar algunos problemas si no agendas a primera hora, ya que lo que tenías planeado puede quedar sin cupos para estudiantes. Además al querer agregar en otro horario las que no alcanzaste puede llegar a tener empalmes de horario, tiempos muertos y con todo esto perder demasiado tiempo al registrar cada horario de cada alumno, provocando que haya colapsos en las páginas de registro por demasiados alumnos intentando agendar.


FODA:

Fortalezas:
Uso de un algoritmo de Backtracking para poder explorar combinaciones sin empalmes
Interfaz web intuitiva
Datos extraídos directamente de SIIAU en tiempo real (Scraping)
Oportunidades:
Interés de alumnos de herramienta que faciliten la inscripción de CUCEI.
Posibilidad de escalar el sistema a otros centros universitarios de UDG.
Implementación y optimizaciones futuras para poder hacer el sistema más rápido y eficiente para los usuarios


Debilidades:
Dependencia de la estructura de SIIAU, si la página llegará a cambiar el scraping puede fallar.
No se puede automatizar la inscripción real (Solo genera los horarios).
El algoritmo tiene un limite de exploración (100,000) para poder tener una respuesta en tiempo real, en un caso extremo de agendar muchas materias el sistema puede no dar la solucion de tener un buen horario.

Amenazas:
Posibles caídas del servidor de SIIAU durante los periodos de las inscripciones.
Que otras personas desarrollen una solucion similar para el registro.


Backlog inicial:


Algoritmo funcional:
El algoritmo base implementado en el archivo api/index.py es un backtracking (Búsqueda con Vuelta atrás).

Funcion:
Se reciben en la pagina las claves de las materias que el alumno quiere cursar.
El sistema consulta en SIIAU y
 obtiene las secciones de las materias.
Se filtran las secciones que no cumplen con los días y horarios disponibles.
Con una función recursiva se prueba una sección de la primera materia, luego una de la segunda, así sucesivamente.
Si en el camino se detecta un empalme de horario, se descarta esa combinación y se retrocede para probar otras opciones.
Al finalizar, las combinaciones válidas se ordenan con los horarios más compactos.


Complejidad Aproximada:
En el peor de los casos, la complejidad temporal del algoritmo es O(N^M), donde N es el número promedio de secciones por materia y M es el número de materias solicitadas. Debido a ese crecimiento que es exponencial , el algoritmo implementa un límite de seguridad de 100,000 evaluaciones para garantizar que la respuesta sea breve.
