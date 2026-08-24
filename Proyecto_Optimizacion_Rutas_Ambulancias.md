# Explicación general: Optimización de rutas de ambulancias en  Montgomery, Pennsylvania.

Documento de lectura sobre el proyecto de optimización de rutas de ambulancias. Resume el problema planteado, los elementos considerados y las restricciones que deberá tener en cuenta el modelo.

**Asignatura:** Toma de Decisiones Organizacionales  
**Dominio:** Logística y optimización de rutas 
**Fuente:** Los datos se obtuvieron de Kaggle en el enlace: https://www.kaggle.com/datasets/mchirico/montcoalert/data  
**Realizado Por:** Juan Esteban Gamba, Jose Gabriel Vega Forero y Sofia Forero Estupiñan

---

## 1. Resumen

El presente proyecto aborda un problema de optimización de rutas de ambulancias para la atención de pacientes en Montgomery, Pennsylvania. Para ello, se busca determinar la secuencia óptima en la que cada ambulancia debe atender a los pacientes, considerando su ubicación geográfica, los tiempos de desplazamiento, el tiempo requerido para la atención de cada paciente, la capacidad limitada de recursos médicos y las restricciones relacionadas con la jornada laboral y el período de almuerzo.

Para la solución del problema se determinará la asignación de pacientes a cada ambulancia y las rutas que permitan minimizar el costo total de operación. Como resultado, el modelo permitio encontrar una solución óptima con un costo mínimo de [Aca ponemos lo que nos vaya a dar el modelo en temas de costos], garantizando el cumplimiento de las restricciones establecidas y una adecuada atención de los pacientes.

De esta manera, el proyecto busca contribuir a una mejor planificación de los recursos disponibles y a una mayor eficiencia en la operación de las ambulancias, considerando tanto los costos de desplazamiento como las condiciones operativas necesarias para la atención de los pacientes.


**Palabras clave:** optimización de rutas, ruteo de vehículos, atención de pacientes, restricciones de tiempo, capacidad.

---

## 2. Introducción

La atención oportuna de pacientes constituye un reto importante para los sistemas de emergencia y servicios de salud, debido a la necesidad de asignar y movilizar eficientemente los recursos disponibles. En este contexto, una planificación adecuada de las rutas de las ambulancias puede contribuir a reducir los tiempos de desplazamiento, mejorar la cobertura de atención y utilizar de manera eficiente los recursos médicos y operativos.

Para este proyecto se propone desarrollar un modelo de optimización aplicado a Montgomery, Pennsylvania, cuyo propósito será determinar las rutas más eficientes para un conjunto de ambulancias encargadas de atender diferentes pacientes ubicados en distintos puntos geográficos del condado. Cada ambulancia iniciará su recorrido desde un punto de origen o estación asignada y deberá desplazarse hacia los pacientes que le sean asignados, considerando la ubicación geográfica de cada uno mediante coordenadas.

El modelo deberá considerar que cada paciente requiere un tiempo específico de atención, por lo que la duración total de una ruta no dependerá únicamente de la distancia o del tiempo de desplazamiento entre los diferentes puntos, sino también del tiempo destinado a la atención de cada paciente. Asimismo, cada ambulancia contará con una cantidad limitada de kits o recursos médicos, lo cual establecerá una restricción sobre la cantidad de pacientes que podrá atender durante su recorrido.

Adicionalmente, la planificación deberá respetar las condiciones de la jornada laboral. Cada ambulancia iniciará su recorrido a una hora determinada y deberá finalizarlo dentro del horario establecido. Durante la jornada se contará con un máximo de seis horas efectivas de operación y un período obligatorio de una hora destinado al almuerzo del personal, durante el cual no se realizarán actividades de desplazamiento ni atención a pacientes. Esta pausa deberá ser considerada dentro de la programación, ya que cualquier variación en los tiempos de desplazamiento o atención puede afectar las visitas posteriores y el cumplimiento del horario establecido.

Por lo tanto, el problema consiste en determinar la asignación de pacientes a cada ambulancia y la secuencia óptima en la que deberán ser atendidos, considerando las restricciones de capacidad, los tiempos de desplazamiento, el tiempo de atención de cada paciente y la jornada laboral. De esta manera, el proyecto busca representar un problema realista de ruteo y asignación de recursos, utilizando información geográfica para determinar rutas eficientes que contribuyan a mejorar la utilización de las ambulancias y la planificación de la atención médica.
