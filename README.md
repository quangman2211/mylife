# RetailOps

Lớp trí tuệ nằm giữa dữ liệu bán hàng rời rạc của shop và người vận hành nó.
Đọc dữ liệu từ KiotViet/Woo/Excel về, chuẩn hoá, rồi cho agent trả lời bằng
tiếng Việt trên dữ liệu thật.

> **Nguyên tắc số 1:** Model chỉ được **xin** và **chỉ tay vào id**.
> Mọi con số thật do code bơm vào. Model không có đường bịa giá hay bịa tồn kho.

## Đang ở đâu

| | Trạng thái |
|---|---|
| Cổng 0 — Kỹ thuật khả thi? | ⬜ **Q0.1 (API KiotViet) chưa trả lời — chặn nhiều nhất** |
| Cổng 1 — Dữ liệu dùng được? | ⬜ |
| Cổng 2 — Agent hữu ích? | ⬜ |
| T3 Hợp đồng dữ liệu | ✅ xong (25 test xanh) |
| Adapter giả | ✅ xong |
| Bộ test hợp đồng | ✅ xong |
| T2 Kho chuẩn hoá + cách ly tenant | ⬜ tiếp theo |
| T4 Lõi agent | ⬜ |
| Adapter KiotViet | 🔒 bị Q0.1 chặn |

## Chạy thử

```bash
pip install pydantic pytest
python -m pytest -q          # 25 test
```

## Cấu trúc

```
docs/
  00-so-quyet-dinh.md         34 câu hỏi chưa biết, xếp theo thứ tự phải biết
  01-architecture-blueprint.md kiến trúc tham chiếu (đọc sau khi qua Cổng 2)
  decisions/                  ADR — mỗi quyết định khó 1 file, ghi VÌ SAO
src/retailops/
  contract/                 ★ T3 — TÀI SẢN CỐT LÕI
    models.py                 hình dạng dữ liệu chung
    base.py                   interface mọi adapter phải theo
  adapters/
    fake.py                   nguồn giả trong bộ nhớ (gỡ thế bí Q0.1)
tests/
  contract_suite.py         ★ test dùng chung cho MỌI adapter
  test_fake_adapter.py        4 dòng — kế thừa là có đủ test
```

## Sáu tầng (blueprint §5.2)

```
T5  GIAO DIỆN        chat · bảng tin · duyệt              ⬜
T4  LÕI AGENT        prompt · skills · gates · staging    ⬜
T3  HỢP ĐỒNG DỮ LIỆU ★ TÀI SẢN ★                          ✅
T2  KHO CHUẨN HOÁ    DB của mình, có shop_id              ⬜
T1  ĐỒNG BỘ          adapter · queue · normalizer         ⬜
T0  NGUỒN CHÂN LÝ    KiotViet · Sapo · Woo · Excel        (không sở hữu)
```

## Ràng buộc bất di bất dịch

Vi phạm là đỏ CI. Chi tiết + lý do: `docs/decisions/0001-*.md`

1. `stock = None` (**không biết**) ≠ `stock = 0` (**hết hàng**)
2. Mọi thứ trả tồn kho bắt buộc kèm `as_of`
3. Nguồn hỏng → ném `SourceUnavailable`, cấm trả rỗng như thể không có hàng
4. Có biến thể `stock=None` → `total_stock` phải là `None`
5. Adapter = 1 instance/shop, `shop_id` gắn lúc khởi tạo

## Thêm một adapter

```python
class TestKiotViet(AdapterContractTests):
    def make_adapter(self, shop_id, *, fail=False):
        return KiotVietAdapter(shop_id, ...)
```

Qua hết bộ test = adapter hợp lệ. Đó là **định nghĩa**, không phải cảm tính.
