---
type: product
tags: [arena, roadmap]
---
# Forge Arena — Estado

## Modelo
Arena corre en la **laptop del PM y se proyecta en la weekly** (modelo local, OQ-03). Por eso el "auth" es **selección de identidad sin password** ([[ADR-013 Arena sin password]]). La moneda es el **SP** ([[Economia CP-SP]]); el PM administra, los devs consumen.

## Construido (WP-18, `305a2cd`) — ⚠️ sin revisión del chat maestro
- `GET /api/players/active` (excluye inactivos), `POST /api/arena/login` (valida activo + `needs_onboarding`), `POST /api/arena/logout` — solo audit_log, sin sesión de servidor.
- Frontend: `/arena/login`, sesión cliente (`frontend/lib/arena-session.tsx`), header con logout, "ver como" desde Ops, redirect a stub `/arena/onboarding`.
- **Pendiente**: evaluar contra el DoD diseñado (estética arcade AC-9.9, inactivos rechazados, localStorage confirmado, banner de impersonación). Ver [[Pendientes y Deuda]].

## Por construir (orden propuesto)
1. **UC-15 Onboarding** — elegir clase + avatar (vuelve real el stub).
2. **UC-10 Mi Perfil** — SP, nivel, historial.
3. **UC-11/12 Leaderboard + detalle SP** — ⚠️ aplicar `LEADERBOARD_AREAS={BE,FE,DESIGN,DB,QA}` (PO fuera) y decidir cómo aparece "Equipo de Producto" (cuenta agregada, no compite como individuo — [[ADR-007 Identidades]]).
4. **UC-13/14 Achievements + tienda** — ACH04 ya se otorga en cierres.

## Deuda que se cobra aquí
`admin_id` hardcoded a 1 (auth real de Ops), guard `require_cost_access()` placeholder de WP-14, banner de UC-17 en Arena (diferido), banner/CTA "Apelar" de UC-06 (apelación hoy se captura presencial en Ops).

Enlaces: [[MOC Casos de Uso]] · [[Pendientes y Deuda]]
