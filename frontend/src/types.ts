export interface ApiImageResult {
  image_url: string

  source_url: string
}

export interface SearchResponse {
  images: ApiImageResult[]

  requested: number

  found: number
}
