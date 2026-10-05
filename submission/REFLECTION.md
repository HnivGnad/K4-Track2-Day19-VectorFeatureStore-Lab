# Reflection — Lab 19

**Tên:** _<Họ Tên>_
**Cohort:** _<A20-K4>_
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

BM25 mạnh nhất ở `exact` vì truy vấn chứa đúng thuật ngữ; hybrid đạt cùng mức
96,7%. Với `paraphrase`, BM25 đạt 33,3%, hybrid 32,0%, còn vector chỉ 24,0%.
Path Lite dùng model tiếng Anh `bge-small-en-v1.5`, nên biểu diễn câu tiếng Việt
chưa tốt. Với `mixed`, hybrid thắng rõ (100%) vì RRF kết hợp tín hiệu từ khóa
và ngữ nghĩa; BM25 đạt 97,0%, vector đạt 98,5%. Trung bình 50 truy vấn, hybrid
cao nhất: 78,6% so với 77,8% của BM25 và 73,2% của vector.

Tôi không dùng hybrid khi truy vấn chủ yếu là mã lỗi, ID, tên sản phẩm hoặc
chuỗi exact và latency/chi phí là ưu tiên; BM25 đơn giản hơn. Pure vector phù
hợp khi người dùng diễn đạt tự do, corpus đa ngôn ngữ và embedding model thực
sự phù hợp như BGE-M3. Dù chọn mode nào, cần đo trên golden set thật.

---

## Điều ngạc nhiên nhất khi làm lab này

Model embedding quan trọng hơn tôi dự đoán: semantic search không tự động thắng
paraphrase nếu ngôn ngữ huấn luyện không khớp corpus.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
