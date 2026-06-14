# UC-14 — Canjear SP por item de tienda

**Tipo:** Forge Arena / Tienda
**Audiencia:** Player + Admin (aprobación)
**Prioridad:** P1 — Cierre del loop de gamificación (SP tiene valor real)
**Sprint objetivo:** Día 6 del MVP

---

## Historia de usuario

Como **Player**, quiero canjear mis SP por items de la tienda (home office, donas, etc.) para que mi esfuerzo se traduzca en algo tangible, y que el canje quede registrado para que el PM lo apruebe y entregue.

---

## Contexto

La tienda cierra el loop de gamificación: SP tiene valor real, no es vanity metric. Bajo el modelo local (OQ-05/OQ-10), los items son perks reales (home office, donas, comida) que el PM entrega offline después de aprobar el canje en la weekly.

Restricciones clave:
- Techo de gasto mensual: 100 SP máximo (OQ-10 ajustada).
- Acumulación indefinida del balance total.
- Workflow: requested → approved → delivered (o rejected).

---

## Criterios de aceptación

**AC-14.1** Existe vista `/arena/shop` accesible desde side nav de Arena.

**AC-14.2** Header con info del wallet:
- Balance total acumulado (gigante).
- Gastado este mes / techo mensual (100 SP) con barra de progreso.
- SP restantes gastables este mes.
- Próximo reset: "Tu techo se renueva el 1 de [mes siguiente]".

**AC-14.3** Catálogo de items:
- Grid de cards, 2-3 columnas.
- Cada card:
  - Icono del item.
  - Nombre.
  - Categoría (perk_time, perk_communal, etc.).
  - Descripción corta.
  - Precio en SP destacado.
  - Notas operativas ("Usar en el sprint siguiente", "Coordinar con PM").
  - Botón "Canjear" (estado depende de condiciones, ver AC-14.4).

**AC-14.4** Estados del botón "Canjear":
- **Habilitado**: player tiene balance + cabe en el techo mensual.
- **Sin saldo**: "Te faltan X SP" (deshabilitado, tooltip explicativo).
- **Techo mensual excedido**: "Excederías el techo mensual (100 SP)" (deshabilitado).
- **Stock agotado**: si `stock_limit` se alcanzó (deshabilitado).
- **Rank insuficiente**: si `min_rank_required` no se cumple (deshabilitado, post-MVP).

**AC-14.5** Click en "Canjear":
- Modal de confirmación con:
  - Item + precio.
  - Balance antes / balance después.
  - Gastado del mes antes / después.
  - Campo opcional "Notas para el PM" (ej. "Quiero usarlo el viernes 28").
- Botones "Cancelar" / "Confirmar canje".

**AC-14.6** Al confirmar:
- Se crea entrada en `redemptions`:
  - `player_id` = self
  - `item_code` = item.code
  - `sprint_id` = sprint actual
  - `sp_spent` = item.price_sp
  - `status` = `'requested'`
  - `requested_at` = NOW()
  - `delivery_notes` = notas si las hubo
- Wallet balance se actualiza inmediatamente (la vista `player_wallet` lo refleja).
- Toast de confirmación: "Canje solicitado. El PM lo aprobará en la próxima weekly."
- Aparece en sección "Mis canjes pendientes".

**AC-14.7** Sección "Mis canjes":
- Tabs: "Pendientes" / "Aprobados" / "Entregados" / "Rechazados".
- Cada canje muestra: item, fecha de solicitud, status, fecha de cambio de estado, notas.
- En "Pendientes": opción "Cancelar canje" (devuelve SP al wallet inmediatamente).

**AC-14.8** Vista admin de canjes pendientes:
- `/admin/shop/redemptions` lista todos los canjes con `status = 'requested'`.
- Filtros: por player, por item, por fecha.
- Acciones por canje:
  - **Aprobar**: cambia status a `approved`, captura `approved_at` y `approved_by`. SP siguen descontados.
  - **Rechazar**: pide razón obligatoria, cambia status a `rejected`. SP se devuelven al wallet (entrada negativa).
  - **Marcar como entregado**: cambia status a `delivered`, captura `delivered_at` y `delivered_by`, permite agregar `delivery_notes` finales.

**AC-14.9** Notificaciones al player:
- Al aprobar: banner en perfil "Canje aprobado: X. Pendiente de entrega."
- Al rechazar: banner "Canje rechazado: razón Y. SP devueltos."
- Al marcar entregado: "Canje entregado. Disfrútalo."
- En MVP local, son banners in-app. Sin push notifications.

**AC-14.10** Validaciones críticas:
- **Wallet no negativo**: si por alguna razón un sub-task se revierte y deja el wallet < 0, los canjes en `requested` se ponen en hold y el PM debe resolver.
- **Doble canje**: si el player intenta canjear el mismo item dos veces en el mismo instante, solo uno se crea (lock pesimista o constraint a nivel app).
- **Inconsistencias**: si el PM rechaza un canje ya `delivered`, requiere razón especial y se registra en `audit_log` con `action_type='delivered_redemption_disputed'`.

**AC-14.11** Modo observación:
- Bajo OQ-08, los primeros 2-4 sprints están en modo observación.
- En este modo, los canjes están bloqueados con banner "Tienda en modo observación. SP visibles pero canjes habilitados a partir del [fecha]."
- El PM puede activar la tienda desde Forge Console.

---

## Entidades involucradas

- `redemptions` — destino principal
- `shop_items` — catálogo
- `players` — wallet del player
- Vistas: `player_wallet`, `monthly_spent_by_player`
- `audit_log` — registro de operaciones
- `sp_adjustments` — devoluciones cuando se rechaza

---

## Reglas de negocio

- **SP se descuentan al solicitar**, no al aprobar. Esto previene double-spending.
- **Cancelación devuelve SP**: el player puede cancelar mientras esté en `requested`.
- **Rechazo devuelve SP**: crea entrada en `sp_adjustments` con `sp_delta` positivo y `adjustment_type='redemption_refund'`.
- **Techo mensual**: validación a nivel app antes de crear el `redemption`. Suma de `sp_spent` de redemptions en `approved` o `delivered` del mes actual + el nuevo canje no puede exceder 100.
- **Acumulación indefinida**: el balance total se acumula sin reset (decisión OQ-10).
- **Items multi-canje**: el mismo item puede canjearse múltiples veces si hay balance y techo disponible.

---

## Out of scope para MVP

- Tienda dinámica (items que aparecen/desaparecen por temporada).
- Items exclusivos por rank (post-MVP).
- Subastas (canjear más SP por item escaso).
- Pago en cripto o moneda real (ya descartado en OQ-10).
- Compra de items para regalar a otro player.
- Sistema de devolución después de entregado.

---

## Dependencias

- **UC-10** (Mi perfil) — wallet integrado.
- **UC-09** (Login) — sesión.
- **Catálogo seed de shop_items** — 8 items iniciales.
- **Motor de SP** — wallet balance calculado.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/arena/shop/items` (catálogo + estado por player).
- [ ] Endpoint POST `/api/arena/shop/redeem` (crear canje).
- [ ] Endpoint POST `/api/arena/shop/redemptions/{id}/cancel` (cancelar pendiente).
- [ ] Endpoint GET `/api/arena/me/redemptions` (mis canjes).
- [ ] Endpoint GET `/api/admin/shop/redemptions?status=requested` (cola admin).
- [ ] Endpoint POST `/api/admin/shop/redemptions/{id}/approve` (aprobar).
- [ ] Endpoint POST `/api/admin/shop/redemptions/{id}/reject` (rechazar con razón).
- [ ] Endpoint POST `/api/admin/shop/redemptions/{id}/deliver` (marcar entregado).
- [ ] Vista `/arena/shop` funcional con catálogo y mis canjes.
- [ ] Vista `/admin/shop/redemptions` funcional.
- [ ] Validación de techo mensual funciona.
- [ ] Modo observación bloquea correctamente.
- [ ] Devolución de SP al rechazar/cancelar.
- [ ] Notificaciones banner in-app funcionales.
