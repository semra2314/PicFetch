import { MAX_COUNT } from "./constants";
import type { SearchResponse } from "./types";

export type SearchErrorKind = "validation" | "server" | "network" | "unexpected";

export class SearchError extends Error {
  constructor(
    public readonly kind: SearchErrorKind,
    message: string,
  ) {
    super(message);
    this.name = "SearchError";
  }
}

// Sunucunun gönderdiği açıklamayı (FastAPI'nin "detail" alanı) okumaya
// çalışır. Gövde boşsa veya JSON değilse sessizce boş döner; çağıran
// taraf o zaman genel bir mesaja düşer.
async function readDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();

    return typeof body?.detail === "string" ? body.detail : "";
  } catch {
    return "";
  }
}

export async function searchImages(keyword: string, count: number): Promise<SearchResponse> {
  let response: Response;

  try {
    response = await fetch("/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ keyword, count }),
    });
  } catch {
    throw new SearchError(
      "network",
      "Sunucuya ulaşılamadı. Bağlantınızı kontrol edip tekrar deneyin.",
    );
  }

  // 400: istek arayüz doğrulamasını geçmiş ama sunucu yine de reddetmiş.
  // Bu genelde kullanıcının düzeltebileceği bir şey değildir, o yüzden
  // sunucunun kendi açıklamasını göstermek genel mesajdan daha yararlı.
  if (response.status === 400) {
    const detail = await readDetail(response);

    throw new SearchError("validation", detail || "Arama isteği sunucu tarafından reddedildi.");
  }

  // 422: Pydantic şema doğrulaması. Buraya düşmesi arayüz doğrulamasının
  // sunucununkiyle uyuşmadığı anlamına gelir.
  if (response.status === 422) {
    throw new SearchError(
      "validation",
      `Arama kelimesini ve 1–${MAX_COUNT} arasındaki görsel sayısını kontrol edin.`,
    );
  }

  if (response.status >= 500) {
    throw new SearchError(
      "server",
      "Arama sunucuda tamamlanamadı. Lütfen daha sonra tekrar deneyin.",
    );
  }

  if (!response.ok) {
    throw new SearchError("unexpected", "Sunucudan beklenmeyen bir yanıt alındı.");
  }

  try {
    return (await response.json()) as SearchResponse;
  } catch {
    throw new SearchError("unexpected", "Sunucunun yanıtı okunamadı.");
  }
}
