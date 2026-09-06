## Purpose

Permite a un jugador autenticado ver, reabrir y continuar sus conversaciones anteriores, y
empezar una conversación nueva sin tener que cerrar sesión, en vez de perder el acceso a ellas
tras el logout.

## ADDED Requirements

### Requirement: Listar conversaciones propias
El sistema SHALL exponer una forma de listar las conversaciones (`chat_sessions`) que
pertenecen únicamente al usuario autenticado, ordenadas de la más reciente a la más antigua,
incluyendo para cada una un identificador, la fecha de creación y un preview corto derivado de
su primer mensaje de usuario. Toda conversación listada SHALL tener al menos un mensaje — ver
"No persistir conversaciones sin interacción".

#### Scenario: Usuario con conversaciones previas
- **WHEN** un usuario autenticado que ya tiene conversaciones pide su lista de conversaciones
- **THEN** el sistema devuelve solo las conversaciones cuyo `user_id` coincide con el usuario
  autenticado, ordenadas de más a menos reciente

#### Scenario: Usuario sin conversaciones previas
- **WHEN** un usuario autenticado que nunca ha chateado pide su lista de conversaciones
- **THEN** el sistema devuelve una lista vacía, no un error

### Requirement: Aislamiento del listado por usuario
El sistema SHALL rechazar cualquier intento de listar o filtrar conversaciones de otro usuario
distinto del autenticado por el token; el `user_id` usado para filtrar SHALL provenir
exclusivamente del token autenticado, nunca de un parámetro de la petición.

#### Scenario: Un usuario no ve conversaciones ajenas
- **WHEN** el usuario A pide su lista de conversaciones
- **THEN** la respuesta no incluye ninguna conversación cuyo dueño sea el usuario B, aunque el
  usuario B tenga conversaciones existentes

### Requirement: Abrir una conversación anterior
El sistema SHALL permitir recuperar el transcript completo (mensajes de usuario y de
asistente, en orden cronológico, con sus fuentes si las tuvieran) de una conversación propia
del usuario autenticado, identificada por su id.

#### Scenario: Abrir una conversación propia
- **WHEN** un usuario autenticado pide el transcript de una de sus propias conversaciones
- **THEN** el sistema devuelve todos sus mensajes en el orden en que fueron creados, con rol,
  contenido y fuentes de cada uno

#### Scenario: Intentar abrir una conversación ajena
- **WHEN** un usuario autenticado pide el transcript de una conversación que pertenece a otro
  usuario, o que no existe
- **THEN** el sistema rechaza la petición sin revelar contenido de la conversación ajena

### Requirement: Continuar una conversación reabierta
El sistema SHALL permitir seguir enviando mensajes nuevos a una conversación previamente
reabierta usando el mismo mecanismo de envío de mensajes ya existente, agregándose al mismo
transcript sin crear una conversación duplicada.

#### Scenario: Enviar un mensaje nuevo tras reabrir
- **WHEN** un usuario reabre una conversación anterior y envía un mensaje nuevo en ella
- **THEN** el mensaje se agrega al transcript de esa misma conversación, a continuación de los
  mensajes previos

### Requirement: Iniciar una conversación nueva bajo demanda
El sistema SHALL permitir a un usuario autenticado obtener un identificador de conversación
nuevo, listo para recibir mensajes, sin necesidad de cerrar sesión y volver a autenticarse.

#### Scenario: Iniciar conversación nueva durante la sesión
- **WHEN** un usuario autenticado pide iniciar una conversación nueva mientras sigue logueado
- **THEN** el sistema le entrega un identificador de conversación nuevo, distinto de cualquier
  conversación previa, asociable a su `user_id` en cuanto reciba un mensaje

### Requirement: No persistir conversaciones sin interacción
El sistema SHALL NOT guardar una conversación (`chat_sessions`) hasta que se le envíe al menos
un mensaje real; obtener un identificador de conversación nuevo — al iniciar sesión o al pedir
una conversación nueva — SHALL NOT por sí solo crear un registro persistente. La conversación
SHALL persistirse en el momento en que llega su primer mensaje, asociada al `user_id`
autenticado que lo envía.

#### Scenario: Login sin enviar ningún mensaje
- **WHEN** un usuario inicia sesión y no envía ningún mensaje
- **THEN** esa conversación no aparece en su lista de conversaciones ni en ningún otro lado,
  porque nunca se persistió

#### Scenario: Nueva conversación sin enviar ningún mensaje
- **WHEN** un usuario pide una conversación nueva y no le envía ningún mensaje
- **THEN** esa conversación no aparece en su lista de conversaciones

#### Scenario: Primer mensaje persiste la conversación
- **WHEN** un usuario envía el primer mensaje usando un identificador de conversación que
  todavía no existe como conversación guardada
- **THEN** el sistema crea la conversación en ese momento, asociada a su `user_id`, y guarda el
  mensaje en ella
