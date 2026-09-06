# chat-progress-indicator Specification

## Purpose

Comunica visualmente al jugador que el agente está procesando su pregunta mientras espera la
respuesta, para que la interfaz nunca parezca congelada durante los varios segundos que puede
tardar la vuelta de RAG + LLM.

## Requirements

### Requirement: Mostrar progreso mientras se procesa el turno
El sistema SHALL mostrar un indicador visible de que el agente está trabajando
(por ejemplo "Pensando..." o "Buscando información...") inmediatamente después de que el
usuario envía un mensaje, y mientras la respuesta del turno todavía no ha llegado.

#### Scenario: Envío de un mensaje
- **WHEN** el usuario envía un mensaje en el chat
- **THEN** el sistema muestra de inmediato un indicador de progreso visible, antes de recibir
  la respuesta del agente

### Requirement: Ocultar el indicador al recibir la respuesta
El sistema SHALL ocultar el indicador de progreso en cuanto llega la respuesta del turno
actual, sin dejar rastros del indicador junto al mensaje de la respuesta.

#### Scenario: Respuesta exitosa
- **WHEN** llega la respuesta del agente para el turno en curso
- **THEN** el sistema oculta el indicador de progreso y muestra el mensaje de respuesta

### Requirement: Ocultar el indicador ante un error
El sistema SHALL ocultar el indicador de progreso también cuando el turno actual termina en
error (por ejemplo, fallo de red o error del backend), y SHALL mostrar el error al usuario en
su lugar.

#### Scenario: El backend responde con error
- **WHEN** la petición del turno en curso falla o el backend responde con un error
- **THEN** el sistema oculta el indicador de progreso y muestra un mensaje de error al usuario

### Requirement: Evitar envíos duplicados durante el procesamiento
El sistema SHALL impedir que el usuario envíe un nuevo mensaje del mismo formulario de chat
mientras el indicador de progreso de un turno anterior sigue visible.

#### Scenario: Intento de reenvío mientras se procesa
- **WHEN** el usuario intenta enviar otro mensaje mientras el indicador de progreso del turno
  anterior todavía está visible
- **THEN** el sistema no envía una segunda petición hasta que el turno en curso termine
