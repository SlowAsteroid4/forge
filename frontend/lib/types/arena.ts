// Tipos de Arena — login / sesión de identidad (UC-09 / WP-18).
// La sesión vive en el cliente (localStorage); no hay sesión de servidor.

export interface ActivePlayerItem {
  id: number;
  display_name: string;
  area: string;
  class_code: string | null;
  avatar_code: string | null;
  role: string | null;
}

export interface ActivePlayersResponse {
  players: ActivePlayerItem[];
  total: number;
}

export interface ArenaSessionProfile {
  id: number;
  display_name: string;
  area: string;
  class_code: string | null;
  avatar_code: string | null;
  role: string | null;
  needs_onboarding: boolean;
}

// Lo que persiste el cliente. `impersonation` = true si el PM entró vía
// "ver como" desde Ops (AC-9.8); entonces se muestra el banner y "Salir" vuelve a Ops.
export interface ArenaSession {
  profile: ArenaSessionProfile;
  impersonation: boolean;
}
