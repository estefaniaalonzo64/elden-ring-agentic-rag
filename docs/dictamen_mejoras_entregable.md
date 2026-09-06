# Dictamen de mejoras del entregable

## Veredicto

El entregable presenta un sistema que cumple conceptualmente con los requisitos de agente conversacional, RAG, memoria y autenticacion simple. La arquitectura esta bien razonada y la URL del servicio esta activa. Sin embargo, antes de la evaluacion debe mejorarse la capacidad de un tercero para comprobar el funcionamiento y la evidencia de las garantias que se declaran.

## Mejoras obligatorias

### 1. Habilitar una evaluacion autenticada

El PDF indica que existen tres cuentas preaprobadas, pero sus credenciales quedan fuera del documento. Por lo tanto, quien reciba solamente la URL y el PDF no puede comprobar el chat, el RAG ni la memoria.

Accion requerida:

- Entregar al docente una cuenta temporal mediante un canal privado, sin incluir su contrasena en el PDF.
- Incluir en el PDF una nota que indique que las credenciales de evaluacion fueron entregadas por separado y el canal utilizado.
- Verificar antes de la entrega que la cuenta permite iniciar sesion y usar el flujo completo.

Criterio de aceptacion: un evaluador autorizado puede abrir la URL, iniciar sesion y probar el sistema sin requerir acceso al repositorio ni intervencion de la autora.

### 2. Demostrar el grounding de forma verificable

El documento afirma grounding estricto, pero no deja claro que exista una barrera de backend ante respuestas sin recuperacion o sin fuentes. No basta con declarar la instruccion del agente: debe quedar demostrado como se evita que el modelo responda sin evidencia del corpus.

Accion requerida:

- Documentar el mecanismo concreto que obliga a recuperar evidencia antes de emitir una respuesta factual.
- Si el control depende del prompt, declararlo como mitigacion y no como garantia dura.
- Agregar un ejemplo de pregunta fuera de corpus, mostrando la negativa del agente.
- Agregar un ejemplo de pregunta dentro de corpus, mostrando las fuentes recuperadas y la respuesta final.

Criterio de aceptacion: el PDF permite distinguir entre una politica declarada en el prompt y una validacion tecnica aplicada en tiempo de ejecucion.

### 3. Incorporar evidencia autosuficiente de pruebas

Las metricas de evaluacion son positivas, pero los soportes citados son rutas locales del repositorio. El PDF debe contener evidencia suficiente para ser revisado por si mismo.

Accion requerida:

- Incluir una tabla breve con al menos tres pruebas completas: RAG con fuentes, memoria entre sesiones y aislamiento entre usuarios.
- Para cada prueba, mostrar entrada, comportamiento esperado, resultado observado y evidencia visible relevante.
- Incluir capturas o transcripciones cortas del servicio desplegado, sin datos sensibles.
- Explicar como se calcularon las metricas y cuantas ejecuciones sustentan cada promedio.

Criterio de aceptacion: un revisor puede entender y auditar el resultado de las pruebas sin abrir archivos externos al PDF.

## Mejoras recomendadas

### 4. Endurecer la persistencia de memoria

El documento reconoce que la actualizacion de preferencias fallo en una conversacion real y que el arreglo se hizo mediante una instruccion mas explicita al LLM. Esto es una mejora valida, pero sigue siendo probabilistica.

Accion recomendada:

- Explicar que la extraccion de memoria depende de una llamada de tool decidida por el modelo.
- Evaluar una validacion de backend o una etapa estructurada que detecte preferencias explicitas y compruebe que se persistieron.
- Mantener una prueba de regresion para declaraciones de preferencias dentro de flujos de recomendacion.

### 5. Reducir privilegios de la cuenta de servicio

Usar `roles/editor` en Cloud Run es una deuda tecnica importante. Aunque esta documentada, no es una configuracion adecuada como objetivo final de produccion.

Accion recomendada:

- Crear una service account dedicada para Cloud Run.
- Reemplazar `roles/editor` por los permisos minimos de BigQuery, Firestore, Vertex AI y Secret Manager que use el servicio.
- Documentar el cambio como una mejora de seguridad posterior si no se alcanza antes de entregar.

### 6. Ajustar foco y forma del PDF

La documentacion es detallada y honesta, pero dedica demasiado espacio a incidentes de Apps Script, correcciones post-MVP y bugs internos. Esa informacion puede condensarse para priorizar la demostracion de los requisitos de la rubrica.

Accion recomendada:

- Reducir la narrativa de incidentes a un bloque corto de decisiones relevantes.
- Usar el espacio liberado para evidencias visuales de login, fuentes RAG y memoria persistente.
- Corregir la pagina 5, que queda casi vacia por paginacion.
- Cambiar la fecha generica "Septiembre 2026" por la fecha concreta de entrega.
- Diferenciar claramente lo implementado antes de la entrega de lo agregado post-MVP.

## Orden de prioridad

1. Proveer acceso autenticado al evaluador.
2. Adjuntar evidencia reproducible de RAG, memoria y aislamiento.
3. Aclarar o reforzar la garantia tecnica de grounding.
4. Mejorar la confiabilidad de la persistencia de memoria.
5. Aplicar minimo privilegio en IAM.
6. Pulir la estructura y paginacion del PDF.
