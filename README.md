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
```

**Venv'i aktive etme:**

```bash
# Windows — Command Prompt
.venv\Scripts\activate

# Windows — PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Aktivasyondan sonra Python bağımlılıklarını kurun:

```bash
python -m pip install -r requirements.txt
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

CLI, pipeline'ı uçtan uca çalıştırır ve doğrulanmış görselleri `data/downloads/`
altına kaydeder.

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
