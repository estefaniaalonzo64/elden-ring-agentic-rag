---
name: frontend-delivery
description: Implementar o modificar el frontend Apps Script (Login/Registro/Chat), su embebido en Google Sites, y la configuración de CORS del backend para que lo acepte. Usar cuando el trabajo toque Code.gs, las pantallas del web app, o la publicación en Sites.
---

# frontend-delivery

Alcance: PRD §25–§27, Fase 7 y 9 (§40), caso de aceptación A/I (§43 vía UI).

## Pantallas — solo estas tres (§25.1)

```text
Login
Registro
Chat
```

No agregar historial de conversaciones, feedback 👍👎, ni endpoints administrativos en la UI
— son TODO-01/02/03, explícitamente fuera del MVP.

## Login (§25.2)

```text
username
password
botón entrar
link registrarse
```

Al hacer login exitoso, guardar en estado de sesión del frontend (no en localStorage
persistente — se limpia al logout, ver §25.4): `token`, `session_id`.

## Chat (§25.3)

```text
mensajes
textarea
botón enviar
logout
```

Cada mensaje enviado va a `POST /chat` con `Authorization: Bearer <token>` y
`{session_id, message}`. Mostrar `message` y, si vienen, las `sources` de la respuesta.

## Estado y logout (§25.4)

```
logout → borrar token → borrar session_id → volver a Login
```

El siguiente login siempre genera una `session_id` nueva (coordinado por el backend, no por
el frontend).

## Estructura de archivos (PRD §31)

```text
frontend/apps-script/
├── Code.gs        # llamadas HTTP al backend (UrlFetchApp), doGet, manejo de estado servidor-side si aplica
├── Index.html     # shell
├── styles.html    # estilos
└── script.html    # lógica cliente (fetch/llamadas a Code.gs, render de pantallas)
```

Si el material de ejemplo del profesor ya trae un patrón Apps Script equivalente, reutilízalo
en vez de reescribir por estética (indicación explícita del PRD §31).

## CORS (§27)

Cloud Run debe permitir solicitudes desde la UI. En el MVP es aceptable una configuración
amplia de CORS en FastAPI para no bloquear la integración Apps Script/Sites — el token sigue
siendo obligatorio para `/chat`, así que la seguridad real no depende de CORS. Documentar esto
como deuda técnica (TODO-06: restringir origins post-MVP), no tratarlo como bug a corregir en
el MVP.

## Google Sites (§26, Fase 9)

```text
1. Publicar el Apps Script como Web App (ejecutar como usuario que accede, acceso: cualquiera).
2. Crear el Google Site.
3. Incrustar el Web App publicado (embed por URL/iframe según lo permita Apps Script).
4. Validar login y chat funcionando end-to-end desde la URL final de Sites.
```

Entregable esperado:

```text
URL Google Sites → Apps Script embebido → servicio Cloud Run activo
```

## Definition of Done de esta pieza

Existe una URL de Google Sites accesible con el Apps Script embebido, desde la cual se puede
registrar, iniciar sesión, chatear y cerrar sesión contra el Cloud Run real (PRD §44).
