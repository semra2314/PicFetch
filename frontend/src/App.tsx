import { useRef, useState } from "react"
import type { FormEvent } from "react"

import { SearchError, searchImages } from "./api"
import { MAX_COUNT } from "./constants"
import type { ApiImageResult } from "./types"

type ViewState = "search" | "loading" | "results" | "empty" | "error"

const SUGGESTIONS = ["kedi", "köpek", "araba", "kuş"]

function sourceLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return "Kaynağı görüntüle"
  }
}

// Bağlantı adresi arama sağlayıcısından geliyor; doğrulanmadan href'e
// yazılırsa "javascript:" gibi bir şema tıklanabilir XSS'e dönüşür.
// React href içeriğini temizlemez, kontrolü burada yapıyoruz.
function isSafeHttpUrl(url: string): boolean {
  try {
    const { protocol } = new URL(url)

    return protocol === "http:" || protocol === "https:"
  } catch {
    return false
  }
}

export default function App() {
  const [view, setView] = useState<ViewState>("search")
  const [keyword, setKeyword] = useState("")
  const [count, setCount] = useState("10")
  const [results, setResults] = useState<ApiImageResult[]>([])
  const [requested, setRequested] = useState(0)
  const [found, setFound] = useState(0)
  const [formError, setFormError] = useState("")
  const [requestError, setRequestError] = useState("")
  const requestId = useRef(0)

  async function runSearch(keywordOverride?: string) {
    const normalizedKeyword = (keywordOverride ?? keyword).trim()
    const normalizedCount = Number(count)

    if (!normalizedKeyword) {
      setFormError("Lütfen aranacak nesneyi yazın.")
      return
    }

    if (
      !Number.isInteger(normalizedCount) ||
      normalizedCount < 1 ||
      normalizedCount > MAX_COUNT
    ) {
      setFormError(
        `Görsel sayısı 1–${MAX_COUNT} arasında bir tam sayı olmalıdır.`,
      )
      return
    }

    setKeyword(normalizedKeyword)
    // İstenen sayıyı şimdiden yaz: bekleme ekranı ham metin state'i yerine
    // normalize edilmiş sayıyı göstersin ("007" değil "7").
    setRequested(normalizedCount)
    setFound(0)
    setFormError("")
    setRequestError("")
    setView("loading")

    // Bu aramanın sıra numarası. Yanıt döndüğünde hâlâ en güncel arama
    // bu mu diye bakarız; değilse (kullanıcı formu sıfırladı ya da yeni
    // bir arama başlattı) geç gelen yanıtı sessizce yok sayarız.
    const currentId = ++requestId.current

    try {
      const response = await searchImages(normalizedKeyword, normalizedCount)

      if (requestId.current !== currentId) {
        return
      }

      setResults(response.images)
      setRequested(response.requested)
      setFound(response.found)
      setView(response.found === 0 ? "empty" : "results")
    } catch (error) {
      if (requestId.current !== currentId) {
        return
      }

      if (error instanceof SearchError) {
        setRequestError(error.message)
      } else {
        setRequestError("Arama tamamlanamadı. Lütfen tekrar deneyin.")
      }

      setView("error")
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void runSearch()
  }

  function resetSearch() {
    // Uçuştaki isteği geçersiz kılar: geç dönerse ekranı ele geçiremez.
    requestId.current += 1

    setView("search")
    setResults([])
    setRequested(0)
    setFound(0)
    setFormError("")
    setRequestError("")
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#05020a] text-slate-200">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -left-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-purple-600/20 blur-[140px]" />
        <div className="absolute -right-40 top-0 h-[32rem] w-[32rem] rounded-full bg-pink-600/15 blur-[140px]" />
        <div className="absolute bottom-0 left-1/3 h-[28rem] w-[28rem] rounded-full bg-cyan-500/10 blur-[150px]" />
      </div>

      <header className="relative z-10 border-b border-white/5 bg-black/10 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <button
            type="button"
            onClick={resetSearch}
            className="flex items-center gap-3"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-purple-400/30 bg-purple-500/10 text-purple-300">
              ◇
            </span>

            <span className="text-lg font-bold tracking-tight text-white">
              Pic<span className="text-purple-400">Fetch</span>
            </span>
          </button>

          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-400">
            YOLOE-26 doğrulama motoru
          </span>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
        {/*
          Ekran okuyucu için durum duyurusu. Görünmez ama view her
          değiştiğinde içeriği güncellendiği için okuyucu yeni durumu
          sesli bildirir. Bu olmadan dakikalarca süren aramanın bittiği
          hiç duyulmaz — odak, artık DOM'da olmayan düğmede kalır.
        */}
        <p className="sr-only" role="status" aria-live="polite">
          {view === "loading" && "Arama sürüyor, lütfen bekleyin."}
          {view === "results" &&
            `Arama tamamlandı. ${requested} istendi, ${found} görsel bulundu.`}
          {view === "empty" && "Doğrulanmış görsel bulunamadı."}
          {view === "error" && requestError}
        </p>

        {view === "search" && (
          <section className="mx-auto max-w-5xl">
            <div className="mb-12 text-center">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-purple-400/20 bg-purple-500/10 px-4 py-2 text-xs font-semibold text-purple-300">
                <span className="h-2 w-2 rounded-full bg-purple-400 shadow-[0_0_14px_rgba(192,132,252,0.8)]" />
                Yapay zekâ destekli görsel doğrulama
              </div>

              <h1 className="text-4xl font-bold leading-tight tracking-tight text-white sm:text-6xl">
                Aradığın görseli bul.
                <br />
                <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent">
                  İçeriğini doğrula.
                </span>
              </h1>

              <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-slate-400">
                PicFetch web üzerinde görsel arar ve sonuçları YOLOE-26 ile
                doğrular. Yalnızca aradığın nesneyi gerçekten içeren görseller
                gösterilir.
              </p>
            </div>

            <form
              onSubmit={handleSubmit}
              className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-5 shadow-2xl shadow-purple-950/30 backdrop-blur-2xl sm:p-7"
            >
              <div className="grid gap-4 md:grid-cols-[1fr_9rem_auto] md:items-end">
                <label className="block">
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Arama kelimesi
                  </span>

                  <input
                    type="text"
                    value={keyword}
                    onChange={(event) => {
                      setKeyword(event.target.value)
                      setFormError("")
                    }}
                    placeholder="Örn. kedi, köpek, kırmızı araba"
                    autoComplete="off"
                    aria-invalid={Boolean(formError)}
                    aria-describedby={formError ? "form-error" : undefined}
                    className="h-12 w-full rounded-xl border border-white/10 bg-black/25 px-4 text-white outline-none transition placeholder:text-slate-500 focus:border-purple-400/50 focus:ring-4 focus:ring-purple-500/10"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Görsel sayısı
                  </span>

                  <input
                    type="number"
                    min="1"
                    max={MAX_COUNT}
                    step="1"
                    value={count}
                    onChange={(event) => {
                      setCount(event.target.value)
                      setFormError("")
                    }}
                    aria-invalid={Boolean(formError)}
                    aria-describedby={formError ? "form-error" : undefined}
                    className="h-12 w-full rounded-xl border border-white/10 bg-black/25 px-4 text-white outline-none transition focus:border-purple-400/50 focus:ring-4 focus:ring-purple-500/10"
                  />
                </label>

                <button
                  type="submit"
                  className="h-12 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 px-7 font-semibold text-white shadow-lg shadow-purple-950/40 transition hover:from-purple-500 hover:to-pink-500 active:scale-[0.98]"
                >
                  Ara ve doğrula
                </button>
              </div>

              {formError && (
                <p
                  id="form-error"
                  role="alert"
                  className="mt-4 rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300"
                >
                  {formError}
                </p>
              )}

              <div className="mt-5 flex flex-wrap items-center gap-2">
                <span className="mr-1 text-xs text-slate-400">Öneriler:</span>

                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      setKeyword(suggestion)
                      void runSearch(suggestion)
                    }}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-400 transition hover:border-purple-400/30 hover:text-purple-300"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </form>

            <div className="mt-10 grid gap-3 text-center sm:grid-cols-3">
              {[
                ["01", "Web araması", "Aday görseller bulunur."],
                ["02", "İndirme", "Görseller güvenli biçimde indirilir."],
                ["03", "Doğrulama", "YOLOE-26 içerikleri kontrol eder."],
              ].map(([number, title, description]) => (
                <div
                  key={number}
                  className="rounded-2xl border border-white/5 bg-white/[0.025] p-5"
                >
                  <span className="text-xs font-bold text-purple-400">
                    {number}
                  </span>
                  <h2 className="mt-2 font-semibold text-white">{title}</h2>
                  <p className="mt-1 text-sm text-slate-400">{description}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {view === "loading" && (
          <section aria-busy="true" className="mx-auto max-w-5xl">
            <div className="rounded-[2rem] border border-purple-400/20 bg-white/[0.05] p-7 backdrop-blur-2xl sm:p-10">
              <div className="mb-9 flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-purple-400">
                    İşlem devam ediyor
                  </p>
                  <h1 className="mt-3 text-3xl font-bold text-white">
                    “{keyword}” görselleri doğrulanıyor
                  </h1>
                  <p className="mt-3 max-w-2xl leading-7 text-slate-400">
                    {requested} görsel isteniyor. Arama, indirme ve model
                    çıkarımı görseller üzerinde sırayla çalışır.
                  </p>
                </div>

                <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-4 py-3">
                  <span className="h-3 w-3 animate-pulse rounded-full bg-purple-400 shadow-[0_0_18px_rgba(192,132,252,0.9)]" />
                  <span className="text-sm text-slate-300">Çalışıyor</span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ["Web aranıyor", "Aday görseller toplanıyor."],
                  ["Görseller hazırlanıyor", "Dosyalar indiriliyor."],
                  ["YOLOE-26 doğruluyor", "Nesne içerikleri kontrol ediliyor."],
                ].map(([title, description]) => (
                  <div
                    key={title}
                    className="rounded-2xl border border-white/5 bg-black/20 p-5"
                  >
                    <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-white/5">
                      <div className="h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-purple-500 to-pink-500" />
                    </div>
                    <h2 className="font-semibold text-white">{title}</h2>
                    <p className="mt-2 text-sm text-slate-400">{description}</p>
                  </div>
                ))}
              </div>

              <p className="mt-8 text-center text-sm leading-6 text-slate-400">
                İstenen görsel sayısına ve bilgisayarın işlem gücüne göre bu
                işlem birkaç dakika sürebilir. Sayfayı kapatmayın.
              </p>
            </div>
          </section>
        )}

        {view === "results" && (
          <section>
            <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">
                  Doğrulama tamamlandı
                </p>
                <h1 className="mt-3 text-3xl font-bold text-white">
                  “{keyword}” sonuçları
                </h1>
                <p className="mt-2 text-slate-400">
                  {requested} istendi, {found} doğrulanmış görsel bulundu.
                </p>
              </div>

              <button
                type="button"
                onClick={resetSearch}
                className="rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white"
              >
                Yeni arama
              </button>
            </div>

            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {results.map((image, index) => (
                <article
                  key={`${image.image_url}-${index}`}
                  className="group overflow-hidden rounded-2xl border border-white/10 bg-white/[0.045] shadow-xl shadow-black/20 transition duration-300 hover:-translate-y-1 hover:border-purple-400/30"
                >
                  <div className="relative aspect-[4/3] overflow-hidden bg-black/30">
                    <img
                      src={image.image_url}
                      alt={`${keyword} doğrulanmış sonucu ${index + 1}`}
                      loading="lazy"
                      className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                    />

                    <span className="absolute right-3 top-3 rounded-full border border-emerald-300/20 bg-emerald-950/80 px-3 py-1.5 text-xs font-semibold text-emerald-300 backdrop-blur">
                      ✓ Doğrulandı
                    </span>
                  </div>

                  <div className="p-4">
                    {isSafeHttpUrl(image.source_url) ? (
                      <a
                        href={image.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate text-sm text-slate-400 transition hover:text-purple-300"
                      >
                        {sourceLabel(image.source_url)} ↗
                      </a>
                    ) : (
                      <span className="block truncate text-sm text-slate-400">
                        Kaynak bağlantısı geçersiz
                      </span>
                    )}

                    <a
                      href={image.image_url}
                      download
                      className="mt-4 flex h-10 items-center justify-center rounded-xl border border-purple-400/25 bg-purple-500/10 text-sm font-semibold text-purple-300 transition hover:bg-purple-500/20"
                    >
                      Görseli indir
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {view === "empty" && (
          <section className="mx-auto max-w-xl text-center">
            <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-10 backdrop-blur-2xl">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-purple-400/20 bg-purple-500/10 text-2xl text-purple-300">
                ◇
              </div>

              <h1 className="mt-6 text-2xl font-bold text-white">
                Doğrulanmış görsel bulunamadı
              </h1>

              <p className="mt-3 leading-7 text-slate-400">
                “{keyword}” için bulunan adaylardan hiçbiri nesne doğrulamasını
                geçemedi. Daha açık veya farklı bir kelime deneyebilirsin.
              </p>

              <p className="mt-4 text-sm text-slate-400">
                {requested} istendi, {found} doğrulanmış görsel bulundu.
              </p>

              <button
                type="button"
                onClick={resetSearch}
                className="mt-7 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 font-semibold text-white"
              >
                Başka bir arama yap
              </button>
            </div>
          </section>
        )}

        {view === "error" && (
          <section className="mx-auto max-w-xl">
            <div className="rounded-[2rem] border border-rose-400/20 bg-white/[0.05] p-8 backdrop-blur-2xl sm:p-10">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-rose-400/20 bg-rose-500/10 text-xl text-rose-300">
                !
              </span>

              <h1 className="mt-6 text-2xl font-bold text-white">
                Arama tamamlanamadı
              </h1>

              <p role="alert" className="mt-3 leading-7 text-slate-400">
                {requestError}
              </p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void runSearch()}
                  className="flex-1 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 px-5 py-3 font-semibold text-white"
                >
                  Tekrar dene
                </button>

                <button
                  type="button"
                  onClick={resetSearch}
                  className="flex-1 rounded-xl border border-white/10 bg-white/5 px-5 py-3 font-semibold text-slate-300"
                >
                  Aramayı düzenle
                </button>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
