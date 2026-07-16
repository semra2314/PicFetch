
from app.downloader.downloader import download
from app.domain import Candidate

candidates = [#başarısız 
    # Açıklama: İlk test listesindeki kedi resmi URL'si (https://upload.wikimedia.org/...) aslında geçerli bir resimdir. Ancak Wikipedia/Wikimedia sunucuları, Python'ın requests kütüphanesinin varsayılan User-Agent başlığını engeller.
    # Sonucu: İstek 403 Forbidden hatası ile döner ve yanıtın içerik türü text/plain olur. Bu sebeple downloader bunu bir görsel olarak algılayamaz (URL görsel değil... - İçerik tipi: text/plain uyarısı verir) ve testi geçerli bir resim olmasına rağmen indiremez. Bu durum downloader tarafında bir User-Agent başlığı tanımlanmamasından kaynaklanır.
    Candidate(url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/1200px-Cat_November_2010-1a.jpg"),
    Candidate(url="https://bozuk-link-test.com/resim.jpg"),  # Bu başarısız olacak
]
results = download(candidates)
print(f"\n Toplam {len(results)} görsel indirildi.")
for img in results:
    print(f"\n URL: {img.url}, Boyut: {len(img.data)} bytes")

candidates = [
    # Picsum.photos - rastgele görsel servisi (gerçek JPEG döndürür)
    Candidate(url="https://picsum.photos/800/600"),
    # Bozuk link - hata yönetimi testi
    Candidate(url="https://bozuk-link-test.com/resim.jpg"),
    # HTML sayfası - içerik tipi testi
    Candidate(url="https://example.com"),
]
results = download(candidates)
print(f"\nToplam {len(results)} görsel indirildi.")
for i, img in enumerate(results, 1):
    print(f"\n {i}. URL: {img.url}, Boyut: {len(img.data)} bytes ({len(img.data) / 1024:.2f} KB)")

# Test dosyası tamamen harici internet sitelerine (picsum.photos, wikimedia, example.com) bağımlıdır. İnternet bağlantısı olmadığında veya bu sitelerde geçici bir kesinti yaşandığında testlerin tamamı başarısız olacaktır.


from app.downloader.downloader import download
from app.domain import Candidate

print("--- TEST BAŞLIYOR ---")

# Sadece 1 tane gerçek, küçük bir resim URL'si test ediyoruz
candidates = [
    Candidate(url="https://picsum.photos/800/600")
]

results = download(candidates)

print(f"\n--- TEST BİTTİ ---")
print(f"Başarıyla indirilen görsel sayısı: {len(results)}")
if len(results) > 0:
    print(f"İndirilen görsel boyutu: {len(results[0].data) / 1024:.2f} KB")