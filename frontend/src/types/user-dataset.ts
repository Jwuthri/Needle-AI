export interface FieldMetadata {
  field_name: string
  data_type: string
  description: string
  unique_value_count?: number | null
  top_values?: string[] | null
}

export interface VectorStoreColumns {
  main_column: string
  alternative_columns: string[]
  description: string
}

export interface UserDataset {
  id: string
  user_id: string
  origin: string
  table_name: string
  description?: string | null
  row_count: number
  field_metadata?: FieldMetadata[] | null
  column_stats?: Record<string, any> | null
  sample_data?: any[] | null
  vector_store_columns?: VectorStoreColumns | null
  meta?: Record<string, any> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface UserDatasetUploadResponse {
  success: boolean
  dataset_id: string
  table_name: string
  row_count: number
  column_count: number
  description: string
  field_metadata: FieldMetadata[]
  column_stats: Record<string, any>
  sample_data: any[]
  vector_store_columns?: VectorStoreColumns | null
}

export interface UserDatasetListResponse {
  datasets: UserDataset[]
  total: number
}

