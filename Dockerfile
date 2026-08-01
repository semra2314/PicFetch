# ---- 1. aşama: frontend build ----
FROM node:22-slim AS frontend
WORKDIR /build
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
# Önce sadece bağımlılık dosyaları: kod değişince pnpm install tekrar koşmasın.
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ---- 2. aşama: uygulama ----
FROM python:3.12-slim
# WORKDIR /app olmak ZORUNDA: model varlıkları build sırasında buraya iniyor,
# runtime'da yine buradan aranıyor. İkisi ayrışırsa model yeniden indirilir.
WORKDIR /app

# Konteynerde stdout bir pipe; Python blok-buffer'a geçer ve loglar gecikmeli
# görünür. Canlıda ilk bakılacak yer log olduğu için bu bir teşhis meselesi.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    YOLO_CONFIG_DIR=/tmp \
    YOLO_AUTOINSTALL=false

# ultralytics/opencv'nin ihtiyaç duyduğu sistem kütüphaneleri.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Önce CPU torch, SONRA requirements.txt. Sıra önemli: pip ikinci adımda
# torch'u kurulu sayar ve CUDA wheel'lerini (nvidia-*) hiç indirmez.
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ultralytics'in metin kodlayıcısı (get_text_pe) modül seviyesinde `clip`
# import ediyor; paket requirements.txt'te YOK. Ultralytics eksik olduğunu
# görünce çalışma zamanında kendi kendine pip install denemesi yapıyor
# (AutoUpdate) ve bu container'da git olmadığı için patlıyordu. Burada
# açıkça kuruyoruz ki build ağsız runtime'a hazır olsun ve kurulum
# kullanıcının makinesinde sürpriz olarak koşmasın.
# Commit SABİTLENMİŞ: dal ucu kayarsa build'ler birbirinden farklı kod alır
# (§4 "sürümler sabitlenmiş" kuralı).
# git yalnızca bu katmanda gerekli, aynı katmanda kaldırılıyor.
# YOLO_AUTOINSTALL=false: başka bir eksik bağımlılık varsa sessizce ağa
# çıkmak yerine build'de patlasın.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && pip install --no-cache-dir \
        "git+https://github.com/ultralytics/CLIP.git@c4b6ea0932a2c0f39a0fa528af5ec4982ff15cab" \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*

COPY app/ ./app/
COPY --from=frontend /build/dist ./frontend/dist

# Model ağırlığı VE get_text_pe'nin metin kodlayıcısı burada iniyor.
# warm_up() gerçek çalışma yolunu koşturduğu için ikisini de indirir;
# sadece .pt kopyalamak yetmezdi.
RUN python -c "from app.detector.detector import warm_up; warm_up()"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]