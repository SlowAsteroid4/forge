"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type {
  PlayerAdminItem,
  PlayerUpdateRequest,
  PlayerAdminUpdateResponse,
  AreaEnum,
  EmploymentType,
} from "@/lib/types/players";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Props {
  player: PlayerAdminItem;
  onClose: () => void;
  onSaved: (updated: PlayerAdminItem) => void;
}

const AREAS: AreaEnum[] = ["BE", "FE", "DESIGN", "DB", "QA", "PO", "PM"];

const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring";
const labelCls = "block text-sm font-medium mb-1";

export function PlayerEditModal({ player, onClose, onSaved }: Props) {
  const [area, setArea] = useState<AreaEnum>(player.area);
  const [employmentType, setEmploymentType] = useState<EmploymentType>(player.employment_type);
  const [isActive, setIsActive] = useState(player.is_active);
  const [isLead, setIsLead] = useState(player.is_lead);
  const [monthlySalary, setMonthlySalary] = useState(
    player.monthly_salary != null ? String(player.monthly_salary) : "",
  );
  const [hourlyRate, setHourlyRate] = useState(
    player.hourly_rate != null ? String(player.hourly_rate) : "",
  );
  const [monthlyHoursCap, setMonthlyHoursCap] = useState(
    player.monthly_hours_cap != null ? String(player.monthly_hours_cap) : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);

    const patch: PlayerUpdateRequest = {};
    if (area !== player.area) patch.area = area;
    if (employmentType !== player.employment_type) patch.employment_type = employmentType;
    if (isActive !== player.is_active) patch.is_active = isActive;
    if (isLead !== player.is_lead) patch.is_lead = isLead;

    const parsedSalary = monthlySalary === "" ? null : Number(monthlySalary);
    const parsedHourly = hourlyRate === "" ? null : Number(hourlyRate);
    const parsedCap = monthlyHoursCap === "" ? null : Number(monthlyHoursCap);

    if (parsedSalary !== player.monthly_salary) patch.monthly_salary = parsedSalary;
    if (parsedHourly !== player.hourly_rate) patch.hourly_rate = parsedHourly;
    if (parsedCap !== player.monthly_hours_cap) patch.monthly_hours_cap = parsedCap;

    if (parsedSalary !== null && parsedSalary < 0) {
      setError("El salario no puede ser negativo.");
      setSaving(false);
      return;
    }
    if (parsedHourly !== null && parsedHourly < 0) {
      setError("La tarifa por hora no puede ser negativa.");
      setSaving(false);
      return;
    }

    try {
      const res = await api.patch<PlayerAdminUpdateResponse>(
        `/admin/players/${player.id}`,
        patch,
      );
      onSaved(res.player);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Editar player</DialogTitle>
        </DialogHeader>

        {/* Campos read-only */}
        <div className="space-y-3 rounded-md bg-muted/40 p-3 text-sm">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            Sincronizado desde Jira — solo lectura
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-muted-foreground">Nombre</label>
              <p className="text-sm font-medium">{player.display_name}</p>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Email</label>
              <p className="text-sm">{player.email ?? "—"}</p>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-muted-foreground">Jira Account ID</label>
              <p className="text-xs font-mono text-muted-foreground">{player.jira_account_id}</p>
            </div>
          </div>
        </div>

        {/* Campos editables */}
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label htmlFor="area" className={labelCls}>Área</label>
              <Select value={area} onValueChange={(v) => setArea(v as AreaEnum)}>
                <SelectTrigger id="area">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AREAS.map((a) => (
                    <SelectItem key={a} value={a}>
                      {a}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label htmlFor="employment_type" className={labelCls}>Tipo</label>
              <Select
                value={employmentType}
                onValueChange={(v) => setEmploymentType(v as EmploymentType)}
              >
                <SelectTrigger id="employment_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="internal">Interno</SelectItem>
                  <SelectItem value="external">Externo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded border"
              />
              <span className="text-sm">Activo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isLead}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setIsLead(e.target.checked)}
                className="h-4 w-4 rounded border"
              />
              <span className="text-sm">Lead</span>
            </label>
          </div>

          {/* Costos — datos sensibles */}
          <div className="border-t pt-3 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Costos (datos sensibles — solo vista admin)
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="monthly_salary" className={labelCls}>Salario mensual (MXN)</label>
                <input
                  id="monthly_salary"
                  type="number"
                  min={0}
                  step={100}
                  placeholder="Ej: 25000"
                  value={monthlySalary}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMonthlySalary(e.target.value)}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="hourly_rate" className={labelCls}>Tarifa/hora (MXN)</label>
                <input
                  id="hourly_rate"
                  type="number"
                  min={0}
                  step={10}
                  placeholder="Ej: 300"
                  value={hourlyRate}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setHourlyRate(e.target.value)}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="monthly_hours_cap" className={labelCls}>Tope horas/mes</label>
                <input
                  id="monthly_hours_cap"
                  type="number"
                  min={0}
                  step={1}
                  placeholder="Ej: 160"
                  value={monthlyHoursCap}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMonthlyHoursCap(e.target.value)}
                  className={inputCls}
                />
              </div>
            </div>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Guardando..." : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
