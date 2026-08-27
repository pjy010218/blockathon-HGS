export type SourceKind = "government" | "community" | "other";

export type Measurement = {
  field: string;
  value: number | string | boolean | null;
  unit?: string | null;
  raw_value?: unknown;
  method?: string | null;
};

export type WaterQualityRecord = {
  id: string;
  ingested_at: string;
  source: {
    kind: SourceKind;
    provider: string;
    dataset_id?: string | null;
    source_record_id?: string | null;
    source_url?: string | null;
  };
  observed_at: string;
  location: { name?: string | null; latitude: number; longitude: number };
  measurements: Measurement[];
  content_hash: string;
  signer_address?: string | null;
  matched_station_id?: string | null;
  matched_station_name?: string | null;
  match_distance_m?: number | null;
  match_status?: "matched" | "unmatched";
  displayable?: boolean;
  blockchain: {
    status: "not_anchored" | "simulated" | "anchored";
    network?: string | null;
    transaction_hash?: string | null;
    contract_address?: string | null;
    block_number?: number | null;
    anchored_at?: string | null;
  };
};

export type GovernmentStation = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  medium?: string | null;
};

export type ComparisonField = {
  field: string;
  government: Measurement | null;
  community: Measurement | null;
  status: string;
};

export type ComparisonResponse = {
  government_record_id: string;
  community_record_id: string;
  fields: ComparisonField[];
  notes: string[];
};
