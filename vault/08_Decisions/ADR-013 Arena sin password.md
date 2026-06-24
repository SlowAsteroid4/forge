---
type: adr
estado: vigente — implementacion sin revisar
fecha: 2026-06
tags: [adr, arena, auth]
---
# ADR-013 — Arena: selección de identidad, sin password

**Contexto.** UC-09 pide "login" de Arena. El modelo operativo real (OQ-03): Arena corre en la laptop del PM y se proyecta en la weekly — no es una app multiusuario expuesta.
**Problema.** Implementar auth real (passwords/JWT/sesiones) para un contexto local sería complejidad sin amenaza que mitigar, y bloquearía Arena tras un sistema de cuentas que nadie pidió.
**Alternativas.** (a) Auth completa; (b) selección de identidad sin password con validaciones mínimas.
**Decisión.** (b): grid de players activos → click = sesión (en el cliente); el backend solo valida `is_active` y devuelve el perfil + `needs_onboarding`; logout simbólico a audit_log; "ver como" desde Ops con banner de impersonación. **El `admin_id` de Ops NO se toca** (auth real de Ops es deuda aparte).
**Consecuencias.** Arena desbloqueada sin sistema de cuentas. La única regla de seguridad: **inactivos no entran**.
**Tradeoffs.** Cero protección entre miembros del equipo — aceptable en el modelo local; revisar si Arena algún día se expone fuera de la laptop del PM. ⚠️ Implementado en WP-18 (`305a2cd`) **sin pasar por el chat maestro** — DoD sin evaluar ([[Pendientes y Deuda]]).
