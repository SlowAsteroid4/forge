# UC-15 — Elegir mi clase y mi avatar desde catálogo predefinido

**Tipo:** Forge Arena / Onboarding y personalización
**Audiencia:** Player
**Prioridad:** P0 — Bloquea acceso completo a Arena (onboarding obligatorio)
**Sprint objetivo:** Día 5 del MVP (junto con UC-09)

---

## Historia de usuario

Como **Player**, quiero elegir mi clase RPG y mi avatar desde un catálogo visual al hacer mi primer login, para tener identidad propia en Arena, y poder cambiarlos eventualmente (con restricciones) si quiero evolucionar mi look.

---

## Contexto

La clase y avatar son la identidad del player en Arena. No afectan SP (cosméticas puras), pero son lo primero que ven los demás en leaderboard y perfil. Bajo OQ-07 acordada, el catálogo es predefinido en MVP (12 clases + 16 avatares); editor pixel-art queda para v0.4.

Restricciones:
- Clase: 1 cambio por trimestre (campo `class_last_changed_at`).
- Avatar: sin restricción de cambio (puramente cosmético).

---

## Criterios de aceptación

**AC-15.1** Existe vista `/arena/onboarding` accesible automáticamente cuando el player loguea por primera vez (`class_code IS NULL` o `avatar_code IS NULL`).

**AC-15.2** El onboarding tiene 3 pasos navegables:

**Paso 1 — Welcome:**
- Pantalla de bienvenida con logo de Forge Arena.
- Breve explicación: qué son SP, qué son las ligas, qué son los buffs.
- Botón "Comenzar".
- Skip no permitido.

**Paso 2 — Elegir clase:**
- Header: "Elige tu clase".
- Grid responsive con las 12 clases del catálogo (`classes` activas).
- Cada card:
  - Sprite/icono de la clase.
  - Nombre + arquetipo.
  - Descripción narrativa (flavor).
  - Estilo visual distintivo según la clase.
- Click selecciona, hover muestra preview.
- Botón "Confirmar clase" al final.

**Paso 3 — Elegir avatar:**
- Header: "Elige tu avatar".
- Grid con los 16 sprites del catálogo (`avatars` activos).
- Cada sprite con su nombre + estilo.
- Click selecciona.
- Preview en grande del avatar + clase combinados (cómo se verá en el perfil).
- Botón "Confirmar y entrar a Arena".

**AC-15.3** Al confirmar el paso 3:
- Se actualiza `players.class_code` y `players.avatar_code`.
- Se setea `players.class_last_changed_at = NOW()`.
- Se registra en `audit_log` (action: `'onboarding_completed'`).
- Se redirige al perfil del player (`/arena/me`) con animación de bienvenida.

**AC-15.4** Cambio posterior de clase:
- Vista `/arena/me/settings` permite cambiar clase.
- Validación: `(NOW() - class_last_changed_at) >= 90 días` (1 trimestre).
- Si no cumple: mensaje "Podrás cambiar de clase en X días" (deshabilitado).
- Si cumple: mismo selector que en onboarding, con confirmación.

**AC-15.5** Cambio de avatar:
- Misma vista `/arena/me/settings`.
- Sin restricción de tiempo.
- Cambio inmediato.

**AC-15.6** Visualización en otras vistas:
- Perfil (UC-10): clase + avatar destacados en header.
- Leaderboard (UC-11): avatar visible, clase como tooltip.
- Achievements (UC-13): avatar en feed del Team Wall.
- Cualquier card de player en la app debe respetar la identidad elegida.

**AC-15.7** Validaciones:
- Player no puede pasar de onboarding sin elegir ambos.
- Combinación clase + avatar es libre (puede ser cualquier mezcla).
- Si el catálogo se actualiza (se agrega o desactiva una clase/avatar), los players existentes mantienen su elección actual. Solo afecta a nuevos onboardings y a quienes cambien.

**AC-15.8** Sugerencias del PM (opcional, MVP):
- Algunas clases tienen "Sugerido para" en el catálogo doc (ej. C01 Archmage → Juan Castillo).
- El PM puede preseleccionar una clase para un player al crear su cuenta (no obligatorio, el player decide al final).
- En MVP no hay sistema formal de sugerencias en UI; es info que el PM comunica offline.

**AC-15.9** Estética del onboarding:
- Pantalla completa, sin distracciones.
- Estética arcade pixel-art consistente.
- Animaciones suaves entre pasos.
- Música de fondo opcional (off por default).

**AC-15.10** Skip emergencia (solo Admin):
- Si por alguna razón el player no puede completar el onboarding, el Admin puede asignarle clase + avatar default desde `/admin/players`.
- En MVP local esto es trivial porque el PM está presente en la weekly.

---

## Entidades involucradas

- `players` — destino del cambio (`class_code`, `avatar_code`, `class_last_changed_at`)
- `classes` — catálogo
- `avatars` — catálogo
- `audit_log` — registro del onboarding

---

## Reglas de negocio

- **Onboarding obligatorio**: ningún player puede acceder a Arena (más allá de `/arena/onboarding`) sin completarlo.
- **Clase = 1 cambio/trimestre**: 90 días desde el último cambio (validado a nivel app).
- **Avatar = libre**: cosmético sin restricción.
- **Sin auto-asignación**: el sistema no asigna clase ni avatar default sin acción del player (excepto el caso de skip de admin).
- **Atomicidad**: si el confirm final del paso 3 falla por error de red, el progreso se preserva — el player puede retomar.

---

## Out of scope para MVP

- Editor pixel-art para crear avatar custom (v0.4).
- Más de 12 clases o 16 avatares (catálogo cerrado en MVP).
- Multi-clase (clase principal + secundaria).
- Skill trees por clase (las clases son puramente cosméticas).
- Cambio de nombre del player (se mantiene `display_name` de Jira).
- Backgrounds o frames por achievements (post-MVP).

---

## Dependencias

- **UC-09** (Login) — onboarding se dispara desde login.
- **Catálogo seed de classes y avatars** — 12 + 16 items respectivamente.
- **Player creado en BD** antes del primer login.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/catalogs/classes` (clases activas).
- [ ] Endpoint GET `/api/catalogs/avatars` (avatares activos).
- [ ] Endpoint POST `/api/arena/onboarding/complete` (envía class_code + avatar_code).
- [ ] Endpoint POST `/api/arena/me/settings/change-class` (con validación 90 días).
- [ ] Endpoint POST `/api/arena/me/settings/change-avatar`.
- [ ] Vista `/arena/onboarding` con 3 pasos navegables.
- [ ] Vista `/arena/me/settings` con cambio de clase y avatar.
- [ ] Validación de 90 días para cambio de clase funciona.
- [ ] Animación de bienvenida al completar onboarding.
- [ ] Perfil refleja inmediatamente la elección.
- [ ] Empty state si catálogos están vacíos: error claro.
