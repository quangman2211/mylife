# ADR-0001 — Viết hợp đồng dữ liệu trước, adapter sau

- **Ngày:** 2026-09-04
- **Trạng thái:** Đã chấp nhận
- **Liên quan:** Blueprint §3.1, §5.2 · Sổ Quyết Định Q0.1

## Bối cảnh

Q0.1 (API KiotViet mở tới đâu) chưa có đáp án. Theo luật của Sổ Quyết Định,
không được viết code cho quyết định bị chặn.

Nhưng ngồi chờ 1 tuần thì mọi thứ khác đứng, kể cả những việc **không** phụ
thuộc câu trả lời đó.

## Quyết định

Viết **hợp đồng dữ liệu (T3) + adapter giả + bộ test hợp đồng** ngay.
**Không** viết adapter KiotViet, **không** viết luồng ghi ngược.

Cơ sở phân loại — với mỗi việc, hỏi 2 câu:

| | Q0.1 ra đáp án khác thì phải vứt? | Khó sửa về sau? | → |
|---|---|---|---|
| Hợp đồng T3 | Không (§3.1: thiết kế theo nhu cầu agent) | **Có** | Làm ngay |
| Adapter giả | Không (không nói chuyện với ai) | Không | Làm ngay |
| Test hợp đồng | Không | Không | Làm ngay |
| Adapter KiotViet | **Có** | — | Hoãn |
| Ghi ngược (P2) | **Có** | — | Hoãn |

## Phương án đã loại

**1. Chờ Q0.1 rồi mới thiết kế hợp đồng theo API KiotViet.**
Loại. Hợp đồng khi đó sẽ mang hình dạng KiotViet, phá nguyên tắc 2 (không
để lộ khái niệm nền tảng). Adapter Woo/Excel sẽ phải bóp méo dữ liệu cho vừa
một khuôn vốn dĩ của KiotViet.

**2. Viết thẳng adapter KiotViet, trừu tượng hoá sau khi có adapter thứ hai.**
Loại. "Trừu tượng hoá sau" nghe hợp lý nhưng ở đây thì không: lúc đó lõi
agent đã viết dựa trên hình dạng KiotViet, và refactor sẽ chạm mọi tầng.
Ngoại lệ này có lý do cụ thể — 8 hàm đọc đã được liệt kê rõ trong blueprint
§3.1, tức là hình dạng đã biết, không phải đang đoán.

**3. Dùng `dict` thay vì model Pydantic.**
Loại. `dict` không bắt được lỗi ở biên. Adapter trả thiếu trường thì lỗi nổ
ở tầng UI, cách chỗ sai 4 tầng.

## Hệ quả

**Tốt:**
- Dựng và ĐO được toàn bộ lõi agent T4 mà không cần KiotViet → mở khoá
  Q2.1, Q2.5, Q2.6, Q0.5, Q3.1, Q3.3
- Adapter mới chỉ tốn 4 dòng test (kế thừa `AdapterContractTests`)
- "Adapter hợp lệ" có định nghĩa chính xác = qua bộ test, không phải cảm tính

**Xấu / chấp nhận:**
- Hợp đồng có thể thiếu trường mà KiotViet có và hữu ích → sẽ phải bổ sung.
  Chấp nhận: thêm trường rẻ, đổi hình dạng đắt.
- Adapter giả là code phải bảo trì thêm.

## Ràng buộc phát sinh — không được vi phạm

1. `stock = None` (không biết) **không bao giờ** được coi như `0` (hết hàng).
2. Mọi thứ trả tồn kho **bắt buộc** kèm `as_of`.
3. Nguồn hỏng phải ném `SourceUnavailable`, **cấm** trả rỗng như thể không có hàng.
4. Có biến thể `stock=None` → `total_stock` **phải** là `None`.
5. Adapter = 1 instance/shop, `shop_id` gắn lúc khởi tạo, không đổi được.

Cả 5 ràng buộc đều đã có test trong `tests/contract_suite.py`. Vi phạm là đỏ CI.
