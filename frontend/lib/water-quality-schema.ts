export type WaterQualityParameterKey =
  | "ph"
  | "dissolved_oxygen"
  | "conductivity"
  | "water_temperature"
  | "nitrate"
  | "nitrite"
  | "hardness"
  | "e_coli";

export type WaterQualityParameter = {
  key: WaterQualityParameterKey;
  label: string;
  unit: string;
  placeholder: string;
  communityField: string;
  emsCodes: readonly string[];
  unitNote?: string;
};

// Canonical frontend contract for the Community ↔ EMS parameter intersection.
// BACKEND INTEGRATION: normalize dataset_download_5399 and this_yr records to
// these keys and units before returning comparisons or accepting submissions.
export const WATER_QUALITY_PARAMETERS: readonly WaterQualityParameter[] = [
  { key: "ph", label: "pH", unit: "pH", placeholder: "7.4", communityField: "ph", emsCodes: ["0004", "PH-F"] },
  { key: "dissolved_oxygen", label: "Dissolved oxygen", unit: "mg/L", placeholder: "9.1", communityField: "oxygen", emsCodes: ["DO-F"] },
  { key: "conductivity", label: "Conductivity", unit: "µS/cm", placeholder: "325", communityField: "conductivity", emsCodes: ["0011", "EC-F"] },
  { key: "water_temperature", label: "Water temperature", unit: "°C", placeholder: "12.8", communityField: "water_temperature", emsCodes: ["TEMF"] },
  { key: "nitrate", label: "Nitrate", unit: "mg/L", placeholder: "0.18", communityField: "nitrates", emsCodes: ["1110"] },
  { key: "nitrite", label: "Nitrite", unit: "mg/L", placeholder: "0.01", communityField: "nitrites", emsCodes: ["1111"] },
  { key: "hardness", label: "Hardness", unit: "mg/L as CaCO₃", placeholder: "118", communityField: "hardness", emsCodes: ["1107"] },
  { key: "e_coli", label: "E. coli", unit: "CFU/100mL", placeholder: "12", communityField: "e_coli", emsCodes: ["0147"], unitNote: "EMS may report MPN/100mL" },
] as const;
