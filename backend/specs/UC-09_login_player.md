# UC-09 — Login del player a Forge Arena

**Tipo:** Forge Arena / Auth
**Audiencia:** Player
**Prioridad:** P0 — Gateway a toda la experiencia Arena
**Sprint objetivo:** Día 5 del MVP

---

## Historia de usuario

Como **Player**, quiero hacer login a Forge Arena de manera sencilla para acceder a mi perfil, ver mis stats, mi posición en el leaderboard y los achievements desbloqueados.

---

## Contexto

Bajo el modelo local (OQ-03), no hay auth con contraseña real. El acceso a Arena durante las weeklys se hace por **selección de identidad** desde una lista de players activos. Esto es suficiente porque:
- La app corre en la laptop del PM.
- Se proyecta en la weekly.
- Los datos no son sensibles en el sentido de seguridad (son datos del equipo, no de clientes).
- La trazabilidad sigue existiendo via `audit_log`.

Cuando se mueva a servidor, se implementará Firebase Auth (decisión revisable en v0.5).

---

## Criterios de aceptación

**AC-9.1** Existe vista pública `/arena/login` accesible sin autenticación previa.

**AC-9.2** La vista muestra:
- Logo de Forge Arena (estética arcade).
- Tagline o frase de bienvenida.
- Grid o lista de avatars/nombres de todos los players activos.
- Cada player muestra: avatar, nombre, clase, área, indicador de "logueado" si ya hay sesión.

**AC-9.3** Click en un player:
- Si no hay sesión activa: lo loguea inmediatamente.
- Si ya hay sesión activa con otro player: pide confirmación "¿Cambiar de player?".
- Si ya hay sesión con el mismo player: redirige a `/arena/home`.

**AC-9.4** El login persiste en la sesión del navegador (localStorage o cookie).
- Cierre del navegador NO cierra sesión automáticamente (modelo local).
- Botón "Logout" disponible siempre en el header de Arena.

**AC-9.5** Onboarding para player nuevo (primer login):
- Si `player.class_code IS NULL` o `player.avatar_code IS NULL`, se redirige a `/arena/onboarding`.
- Onboarding tiene 3 pasos:
  1. **Bienvenida**: explicación corta de Arena, las ligas, los SP.
  2. **Elegir clase**: catálogo visual de las 12 clases con descripción y arquetipo. (UC-15)
  3. **Elegir avatar**: catálogo visual de los 16 sprites. (UC-15)
- Al terminar, redirige a `/arena/home`.

**AC-9.6** Después del primer onboarding, futuros logins van directo a `/arena/home`.

**AC-9.7** Si un player NO es activo (`is_active=0`) no aparece en la lista de login. Si conoce la URL directa, el sistema rechaza el login.

**AC-9.8** El PM tiene un atajo: puede "ver como X player" desde Forge Ops sin perder su sesión admin. Esto es útil para verificar qué ve cada uno en weeklys. La sesión "impersonada" está claramente marcada con un banner.

**AC-9.9** Visual de la vista de login:
- Estética arcade pixel-art según design system.
- Animaciones sutiles (pulse en avatares al hover).
- Música/sonidos opcionales en futuras versiones (post-MVP).

**AC-9.10** Validaciones:
- Si no hay players activos en la BD: muestra "No hay players activos. Contacta al PM."
- Si la BD no es accesible: error claro con instrucciones.

---

## Entidades involucradas

- `players` — fuente del listado y target del login
- `classes`, `avatars` — para mostrar en la lista
- `audit_log` — registro de logins (opcional en MVP)

---

## Reglas de negocio

- **Sin contraseña en MVP**: el login es selección de identidad. La protección es física (la laptop del PM).
- **Una sesión por navegador**: cambiar de player implica logout del anterior.
- **Onboarding obligatorio**: nadie puede entrar a Arena sin clase + avatar seleccionados.
- **Players nuevos**: cuando se agrega un player al equipo, aparece automáticamente en la lista de login.
- **PM también puede ser player**: si el PM además es player (caso de Saúl que también podría tener perfil), aparece en la lista. Su rol admin se preserva al navegar a Ops.

---

## Out of scope para MVP

- Auth real con contraseña.
- Recuperación de contraseña.
- 2FA.
- Login con Google/Microsoft (SSO).
- Multi-device sync de sesión.
- Login con QR code.
- Roles granulares (Player vs Lead diferenciados en Arena).

---

## Dependencias

- **Seed inicial de players** debe estar cargado.
- **Catálogos de classes y avatars** deben estar disponibles.
- **UC-15** (Selección de clase/avatar) — flujo de onboarding.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/players/active` implementado.
- [ ] Endpoint POST `/api/arena/login` (recibe player_id, crea sesión).
- [ ] Endpoint POST `/api/arena/logout`.
- [ ] Vista `/arena/login` funcional con estética arcade.
- [ ] Vista `/arena/onboarding` para primer login.
- [ ] Persistencia de sesión en localStorage.
- [ ] Redirección automática si ya hay sesión.
- [ ] "Ver como" desde Ops funciona y muestra banner de impersonación.
- [ ] Empty state cuando no hay players activos.
- [ ] Header global de Arena tiene botón Logout siempre visible.
