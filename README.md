# PicFetch

Kullanıcının verdiği bir kelimeye göre web'den görsel arayan, **YOLOE-26** ile o kelimenin
görselde bulunup bulunmadığını doğrulayan bir görsel arama sistemi.

Sıradan bir görsel aramasından farkı şu: arama motorunun döndürdüğü sonuçlara güvenmez.
Her adayı indirir, açık-sözcük bir nesne tespit modelinden geçirir ve yalnızca modelin
aranan nesneyi tespit ettiği görselleri gösterir. Bu yüzden **"50 istendi, 22 bulundu"
gibi bir sonuç normaldir ve bir hata değildir.**

**Akış:** `kelime + adet` → arama → indirme → tekilleştirme → tespit (YOLOE-26) →
süzme/sıralama → diske yazma → kullanıcıya sunum

İki giriş kapısı vardır: bir **web arayüzü/API** (FastAPI) ve bir **CLI** (terminal).
İkisi de aynı çekirdeği çağırır.

---

## Gereksinimler

| Bileşen | Sürüm | Ne için |
|---|---|---|
| Python | 3.12 | Backend |
| Node.js | 22+ | Arayüz derlemesi |
| pnpm | 9 | Arayüz paket yöneticisi |
| Docker | — | Alternatif kurulum (Node/Python gerekmez) |

Disk: model ağırlığı (~67 MB) ve metin kodlayıcı (~242 MB) ilk çalıştırmada iner.

**GPU gerekmez.** Sistem CPU'da çalışır; doğrulama aşaması yavaşlar ama diğer aşamalar
etkilenmez. Ayrıntı için "Ne kadar sürer?" bölümüne bakın.

---

## Kurulum

### Seçenek A — Docker (önerilen)

Node ve Python kurulumu gerektirmez; arayüz derlemesi image içinde yapılır.

```bash
git clone https://github.com/semra2314/PicFetch.git
cd PicFetch

docker compose up --build
```

Ardından `http://localhost:8000` adresini açın.

İlk build **ağ hızına göre 10–30 dakika** sürer. Sürenin çoğu model ağırlığı (67 MB) ve
metin kodlayıcının (242 MB) indirilmesine gider; ikisi de image'a gömülür, böylece
container her açıldığında yeniden inmez ve açılış birkaç saniye sürer.

Durdurmak için:

```bash
docker compose down
```

> `docker-compose.yml` içinde `restart: unless-stopped` tanımlı — container kendini
> yeniden başlatır. Terminali kapatmak yetmez, açıkça `down` demeniz gerekir.

İndirilen görseller `data/` altında kalır; container silinse de durur.

**Docker image CPU torch kullanır** (bilinçli tercih, `Dockerfile` içinde açıkça
kurulur). GPU'lu bir makinede ölçüm yapacaksanız yerel kurulumu kullanın.

### Seçenek B — Yerel kurulum (venv)

```bash
git clone https://github.com/semra2314/PicFetch.git
cd PicFetch

python -m venv .venv
```

**Venv'i aktive edin:**

```bash
# Windows — Command Prompt
.venv\Scripts\activate

# Windows — PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

**Python bağımlılıkları:**

```bash
python -m pip install -r requirements.txt
```

> **Not — `clip` bağımlılığı.** Ultralytics'in metin komutu yolu (`get_text_pe`),
> `requirements.txt`'te bulunmayan bir `clip` paketine ihtiyaç duyar. Docker imajında bu
> paket sabitlenmiş bir commit'ten açıkça kurulur. Yerel kurulumda ise ultralytics
> eksikliği ilk arama sırasında fark eder ve kendi kendine kurmayı dener; bu deneme
> sessizce ağa çıkar ve bazı ortamlarda (git yoksa) başarısız olur. Sorun yaşarsanız
> aynı sürümü elle kurun:
>
> ```bash
> pip install "git+https://github.com/ultralytics/CLIP.git@c4b6ea0932a2c0f39a0fa528af5ec4982ff15cab"
> ```

**Arayüz (frontend):**

Arayüz Vite + React ile derlenir; Python bağımlılıklarından ayrıdır.

```bash
npm install -g pnpm@9      # pnpm kurulu değilse

cd frontend
pnpm install --frozen-lockfile
pnpm build                  # frontend/dist üretir
cd ..
```

`pnpm build` çalıştırılmazsa sunucu yine ayağa kalkar, ancak `/` adresi **503** döner ve
logda "Frontend build bulunamadı" uyarısı görünür. API (`/search`, `/health`) build
olmadan da çalışır.

> `uvicorn --reload` yalnızca `.py` dosyalarını izler. Arayüzde yaptığınız değişiklik
> `pnpm build` çalıştırılmadan tarayıcıya yansımaz.

---

## Çalıştırma

### Web

```bash
uvicorn app.main:app --reload
```

- `http://127.0.0.1:8000/` — arayüz (önce `pnpm build` gerekir)
- `http://127.0.0.1:8000/health` — sağlık kontrolü ve `max_count` değeri
- `http://127.0.0.1:8000/docs` — otomatik API dokümantasyonu

**Açılışta ısıtma:** Sunucu, ilk isteği beklemeden modeli yükler ve küçük bir görselle tek
bir çıkarım koşturur. Böylece ilk arama yapan kişi model yükleme bedelini ödemez. Bu adım
başarısız olursa **uygulama hiç başlamaz** — bilinçli tercih: "ok" diyen ama her aramada
patlayan bir sunucu, hiç açılmayan bir sunucudan daha zor teşhis edilir.

`--reload` ile geliştirirken her yeniden başlatmada ısıtma süresi ödenir.

### CLI

```bash
python -m app.cli "cat" --count 5
```

`--count` verilmezse varsayılan 10'dur; üst sınır `config.MAX_COUNT`'tur.

CLI, zinciri uçtan uca çalıştırır ve doğrulanmış görselleri `data/downloads/` altına
kaydeder. Bir ürün değil, **doğrulama aracıdır**: "sistem gerçekten çalışıyor mu"
sorusunu tarayıcı gürültüsü olmadan cevaplamak için vardır.

### API'yi doğrudan kullanma

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"keyword": "cat", "count": 5}'
```

Yanıt, her görsel için sunucudaki adresi (`image_url`) ve orijinal kaynağı (`source_url`)
taşır; ayrıca `requested` ve `found` sayılarını döndürür. Görseller `image_url` üzerinden
`/static/...` altından servis edilir.

---

## Bilinmesi gerekenler

### Ne kadar sürer?

Beklemenin büyük kısmı **indirme** aşamasında geçer. GPU'lu bir dizüstü bilgisayarda
medium modelle yapılan bir ölçümde 50 görsellik bir arama uçtan uca ~39 saniye sürdü
ve şöyle dağıldı:

| Aşama | Süre | Pay |
|---|---|---|
| Arama | ~1 sn | %3 |
| İndirme | ~32 sn | %82 |
| Doğrulama | ~6 sn | %15 |

Bu dağılım donanıma bağlıdır ve CPU'lu makinelerde doğrulamanın payı belirgin biçimde
büyür; arama ve indirme süreleri donanımdan etkilenmez.

Aynı model ve aynı görsellerle yapılan ölçümde görsel başına çıkarım süresi **GPU'da
~63 ms, CPU'da ~409 ms** çıktı (dizüstü bilgisayar, medium model) — yaklaşık **6,5
kat** fark.

Model boyutu ikinci bir çarpan. 2 çekirdekli bir bulut sunucusunda (Hetzner CX, 4 GB)
görsel başına çıkarım medium modelde **~2,1 sn**, small modelde **~0,78 sn** ölçüldü.
Aradaki ~2,7 katlık fark modelden geliyor; dizüstü CPU'suyla arasındaki fark ise
muhtemelen çekirdek sayısı ve saat hızından. Proje varsayılan olarak small kullanır
(bkz. `MODEL_NAME`).

Doğrulama, istenen sayıya ulaşıldığı anda durur (bkz. "Sonuçlar en iyi eşleşmeler
mi?"). Bu yüzden doğrulama oranı yüksek kelimelerde arama belirgin biçimde daha hızlı
biter.

Arayüz beklerken geçen süreyi gösterir ve arama bitince toplam süreyi ekranda bırakır.
Uzun bekleme **normaldir**, takılma değildir.

### "İstenen sayıya ulaşılamadı" neden olur?

Doğrulama oranı kelimeye göre ciddi biçimde değişir. Small modelle, 50 görsel istenerek
yapılan ölçümler:

| Kelime | İncelenen | Eşiği geçen | Not |
|---|---|---|---|
| laptop | 50 | 50 | erken çıkış |
| elephant | 50 | 50 | erken çıkış |
| bicycle | 54 | 50 | erken çıkış |
| pizza | 61 | 50 | erken çıkış |
| umbrella | 52 | 46 | %88 |
| coffee cup | 61 | 44 | %72 |
| clock | 66 | 37 | %56 |
| sunflower | 78 | 40 | %51 |
| backpack | 89 | 42 | %47 |
| hammer | 73 | 18 | %25 |
| guitar | 84 | 16 | %19 |
| handsaw | 74 | 11 | %15 |
| tractor | 79 | 9 | %11 |
| kettle | 80 | 8 | %10 |

"Erken çıkış" satırlarında havuzun tamamı taranmadığı için oran hesaplanamaz; bu
kelimelerde sistem istenen sayıyı sorunsuz buluyor demektir.

Düşük oranların birkaç ayrı sebebi var:

**Model nesneyi tanımıyor.** Nesnenin doğranmış, dilimlenmiş, çizim/logo hâlinde veya
kadrajı dolduracak biçimde göründüğü görsellerde model zorlanır. `tractor`
sonuçlarının çoğu geniş tarla manzarasıdır ve traktör kadrajın küçük bir kısmını
kaplar. `forest` gibi sahne isimlerinde ise nesne düzeyinde kutu çizilecek bir örnek
yoktur.

**Arama katmanı alakasız görsel getiriyor.** Bu bir doğrulama sorunu değildir ve
düşük oranı modele yazmak yanıltıcı olur. Ölçülen örnekler: `iron` (6/83) sonuçları
periyodik tablo ve anemi infografikleriyle doludur — `clothes iron` aynı nesne için
29/60 verir. `saw` (4/70) aynı adlı filmin afişlerini getirir; `handsaw` 11/74 verir.
Log'daki URL'lere bakmak, sorunun hangi katmanda olduğunu genellikle hemen gösterir.

**Kelime modelin beklediği anlamda değil.** `mouse` 50/90 ile bilgisayar faresi
bulur; `mouse animal` ise gerçek fare fotoğraflarında 3/79 verir. Model için "mouse"
bir çevre birimidir.

Bu bir hata değil, sistemin sınırıdır — durum "50 istendi, 22 bulundu" diyerek
dürüstçe gösterilir. İstediğiniz sayıya ulaşamıyorsanız somut ve tekil bir nesne adı
denemek genellikle işe yarar.

### Kelime seçimi hakkında bilinmeyenler

Aşağıdaki iki konuda **çelişkili gözlemler** var ve temiz bir ölçüm yapılmadı. Kural
olarak yazmıyoruz:

- **Dil.** Arayüz "yalnızca İngilizce kelimeler destekleniyor" uyarısı gösterir. Ancak
  Türkçe kelimelerle de sonuç alındığı gözlendi. Metin kodlayıcı ağırlıklı
  olarak İngilizce veriyle eğitildiği için İngilizce kelimelerin daha iyi çalışması bekleniyor.


### Sonuçlar en iyi eşleşmeler mi?

Tam olarak değil. Sistem, eşiği geçen istenen sayıda görsele ulaştığı anda doğrulamayı
durdurur; kalan adaylar hiç incelenmez. Dönen liste kendi içinde güven skoruna göre
sıralıdır, ancak "havuzdaki en iyi N görsel" olduğu **garanti edilmez**. Bu, hız lehine
verilmiş bilinçli bir takastır.

`DETECT_THRESHOLD` cömert bir eşiktir (0.25); peluş oyuncak, çizim veya logo gibi
sonuçlar da listeye girebilir.

### Veriler nerede?

- `data/downloads/` — doğrulanmış görseller, içerik hash'iyle adlandırılır
  (`ab/abcd1234….jpg`). Aranan kelime dosya yoluna hiç girmez.
- Aynı içerik iki kez inse bile tek dosya olarak durur.
- **Otomatik temizlik yoktur.** Klasör zamanla büyür; gerektiğinde elle boşaltın.

---

## Yapılandırma

Tüm ayarlar `app/config.py` içindedir ve her sabitin yanında *ne işe yarar / neden bu
değer / değişirse ne olur* açıklaması bulunur. Sık dokunulanlar:

| Sabit | Varsayılan | Ne yapar |
|---|---|---|
| `MAX_COUNT` | 50 | Tek istekte istenebilecek en fazla görsel |
| `DETECT_THRESHOLD` | 0.25 | Bir tespitin "geçerli" sayılması için gereken güven skoru |
| `OVERFETCH` | 2 | İstenenin kaç katı aday çekileceği |
| `SEARCH_MAX_PAGES` | 3 | Aramada en fazla kaç sonuç sayfası çekileceği |
| `SEARCH_BACKEND` | `bing` | Kullanılacak arama motoru |
| `MAX_CONCURRENT_DOWNLOADS` | 12 | Aynı anda kaç indirme çalışacağı |
| `DOWNLOAD_TIMEOUT` | 4 | Bir indirme için beklenecek en fazla süre (sn) |
| `MODEL_NAME` | `yoloe-26s-seg.pt` | Kullanılan model dosyası |

> `SEARCH_BACKEND`'e geçersiz bir motor adı yazılırsa kütüphane hata vermez, sessizce
> otomatik seçime döner. Değiştirirken log'dan hangi motorun çalıştığını doğrulayın.

Log seviyesi `LOG_LEVEL` ortam değişkeninden okunur (varsayılan `INFO`):

```bash
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

Her arama tek satırlık bir özet log basar:

```
Arama özeti keyword='car' istenen=50 sorulan=100 aday=93 inen=88 tekil=88 incelenen=62 esigi_gecen=50
```

| Alan | Anlamı |
|---|---|
| `istenen` | Kullanıcının istediği görsel sayısı |
| `sorulan` | Aramadan istenen aday sayısı (`istenen × OVERFETCH`) |
| `aday` | Aramanın döndürdüğü tekil URL sayısı |
| `inen` | Başarıyla indirilen dosya sayısı |
| `tekil` | İçerik olarak birbirinden farklı olanlar |
| `incelenen` | Modelden geçirilen görsel sayısı |
| `esigi_gecen` | Eşiği geçen, yani kullanıcıya sunulabilecek olanlar |

Bir sorunun hangi aşamada olduğunu anlamak için ilk bakılacak yer burasıdır. İki karşılaştırma
özellikle işe yarar: `sorulan` ile `aday` arasındaki fark arama katmanının yetersiz
kaldığını, `incelenen` ile `tekil` arasındaki fark ise doğrulamanın erken durduğunu
gösterir (`incelenen = tekil` ise havuzun tamamı taranmış, istenen sayıya ulaşılamamış
demektir).

---

## Geliştirme

Commit atmadan önce:

```bash
ruff check .
ruff format .
mypy app
pytest tests/ --ignore=tests/integration
```

Frontend tarafında:

```bash
cd frontend
pnpm typecheck              # tsc --noEmit
pnpm build
pnpm exec oxfmt .           # biçimlendir
pnpm exec oxfmt --check .   # sadece kontrol et
```

**Entegrasyon testi** gerçek modeli çalıştırdığı için yavaştır ve CI'da koşmaz; elle
çalıştırılır:

```bash
pytest tests/integration
```

CI her PR'da ruff, mypy ve birim testlerini koşturur.
