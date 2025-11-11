export interface FieldMetadata {
  field_name: string
  data_type: string
  description: string
  unique_value_count?: number | null
  top_values?: string[] | null
}

export interface UserDataset {
  id: string
  user_id: string
  origin: string
  table_name: string
  dynamic_table_name: string
  description?: string | null
  row_count: number
  meta?: {
    field_metadata?: FieldMetadata[]
  } | null
  created_at?: string | null
  updated_at?: string | null
}

export interface UserDatasetUploadResponse {
  success: boolean
  dataset_id: string
  table_name: string
  dynamic_table_name: string
  row_count: number
  column_count: number
  description: string
  field_metadata: FieldMetadata[]
}

export interface UserDatasetListResponse {
  datasets: UserDataset[]
  total: number
}

