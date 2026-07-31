export interface ApiImageResult {
  image_url: string;
  source_url: string;
}

export interface HealthResponse {
  status: string;
  max_count: number;
}

export interface SearchResponse {
  images: ApiImageResult[];
  requested: number;
  found: number;
}
