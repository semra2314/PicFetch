# PicFetch

Kullanıcının verdiği bir kelimeye göre web'den görsel arayan, YOLOE-26 ile o kelimenin
görselde gerçekten olup olmadığını doğrulayan bir görsel arama sistemi.

> **Durum:** Faz 0 — proje iskeleti kuruldu. Modüllerin (`search`, `downloader`, `detector`,
> `ranking`) içi henüz boş (`...`); yalnızca tipler ve fonksiyon imzaları tanımlı.

## Kurulum

```bash
git clone https://github.com/semra2314/PicFetch.git
cd PicFetch

python -m venv .venv
pip install -r requirements.txt
```

**Venv'i aktive etme:**
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

**Frontend (web arayüzü):**

Arayüz Vite + React ile derlenir; Python bağımlılıklarından ayrıdır.
Node.js 22+ ve pnpm 9 gerektirir.

```bash
npm install -g pnpm@9      # pnpm kurulu değilse

cd frontend
pnpm install --frozen-lockfile
pnpm build                  # frontend/dist üretir
cd ..
```

`pnpm build` çalıştırılmazsa sunucu yine ayağa kalkar, ancak `/` adresi 503 döner ve
logda "Frontend build bulunamadı" uyarısı görünür. API (`/search`, `/health`) build
olmadan da çalışır.

## Çalıştırma

**Web (FastAPI):**
```bash
uvicorn app.main:app --reload
```
- `http://127.0.0.1:8000/` — arayüz (önce `pnpm build` gerekir)
- `http://127.0.0.1:8000/health` — sağlık kontrolü

**CLI (terminal):**
```bash
python -m app.cli "kedi" --count 5
```

> **Not:** CLI şu an sadece verdiğiniz argümanları (`keyword`, `count`) ekrana yazdırır;
> gerçek arama/indirme/tespit mantığı Faz 1'de eklenecek.

## Geliştirme

Commit atmadan önce:
```bash
ruff check .
ruff format .
```

Frontend tarafında:
```bash
cd frontend
pnpm typecheck              # tsc --noEmit
pnpm exec oxfmt .           # biçimlendir
pnpm exec oxfmt --check .   # sadece kontrol et
```
