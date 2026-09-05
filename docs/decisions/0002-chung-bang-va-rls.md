# ADR-0002 — Chung bảng + Row Level Security, không phải schema-per-tenant

- **Ngày:** 2026-09-04
- **Trạng thái:** Đã chấp nhận
- **Sửa lại:** Blueprint §6.3 (bản đó chọn schema-per-tenant)
- **Liên quan:** Rủi ro R1 · Sổ Quyết Định Q5.4

## Bối cảnh

Blueprint §6.3 xếp ba phương án:

```
① Chung bảng + cột shop_id   → "rẻ nhất, RỦI RO CAO NHẤT"
② Schema per tenant          → đã chọn
③ Database per tenant        → an toàn nhất, vận hành nặng
```

Và đề xuất: MVP dùng ①, viết code như ②, khi lên ~10 shop thì chuyển sang ②
"mà không đổi code tầng trên".

## Vấn đề với lập luận đó

**Nhãn "rủi ro cao nhất" của ① chỉ đúng với một cách làm ①** — cách để code
ứng dụng tự thêm `WHERE shop_id = ...`. Cách đó dựa vào trí nhớ của người
viết code lúc 2h sáng, và đúng là nguy hiểm.

Nhưng Postgres có Row Level Security: **database tự từ chối trả dòng của
shop khác**, kể cả khi code quên `WHERE`, kể cả khi ai đó mở psycopg gọi
SQL thẳng. Đó vẫn là ① nhưng hồ sơ rủi ro hoàn toàn khác.

**Và câu "chuyển ①→② không đổi code tầng trên" không đúng về mặt kỹ thuật.**
Chuyển đổi routing kết nối, trình chạy migration, và chiến lược backup.
Nó không miễn phí.

## Quyết định

Dùng **① + RLS**, có `FORCE ROW LEVEL SECURITY`, ứng dụng chạy bằng vai
trò không phải superuser và không phải chủ bảng.

| Phương án | Ai chặn rò dữ liệu | Vận hành ở 50 shop |
|---|---|---|
| ①-ngây thơ | Người viết code nhớ | Thấp |
| **①-RLS** | **Database** | **Thấp — 1 migration, 1 pool** |
| ② Schema/tenant | Ranh giới schema | Cao |
| ③ DB/tenant | Ranh giới DB | Rất cao |

## Ba chi phí ẩn của ② mà blueprint không nêu

1. **Migration chạy N lần.** Thêm một cột ở 50 shop = 50 lần chạy. Lần thứ
   37 hỏng giữa chừng thì hệ thống có hai phiên bản schema cùng lúc, và
   code phải chịu được cả hai.
2. **Connection pool.** Mỗi schema cần `search_path` riêng → hoặc 50 pool
   riêng, hoặc set `search_path` mỗi lần mượn kết nối. Vế sau đúng là lỗi
   mà RLS cũng gặp — nhưng ở ② không có lưới an toàn nào phía dưới.
3. **Bảng tin operator** (blueprint §3.7) cần đọc chéo mọi shop → phải
   `UNION` 50 schema, và danh sách schema thay đổi mỗi khi có khách mới.

## Bốn lớp phòng thủ

| Lớp | Cơ chế | Dev mệt phá được? |
|---|---|---|
| 1. Schema | `shop_id NOT NULL`, PK gộp shop_id, FK gộp shop_id | Được |
| 2. Repository | Nhận `ShopScope`, không nhận `Connection` | Được |
| 3. **RLS** | **Postgres từ chối** | **Không** |
| 4. Test tấn công | 24 test, chạy mỗi lần push | Không (đỏ CI) |

Lớp 1–2 chỉ để lỗi nổ sớm và dễ đọc. **Lớp 3 là lớp thật.**

## Chi tiết dễ sai — đều đã có test canh

| Chi tiết | Sai thì sao |
|---|---|
| `FORCE ROW LEVEL SECURITY` | Thiếu → chủ bảng đi xuyên policy |
| App **không** phải superuser | Superuser đi xuyên RLS, mọi policy thành trang trí |
| `SET LOCAL` chứ không phải `SET` | Scope rò qua connection pool sang shop khác |
| `set_config()` tham số hoá | Nối chuỗi → SQL injection qua subdomain |
| `WITH CHECK` ngoài `USING` | Thiếu → shop A ghi đè được dữ liệu shop B |
| `current_setting(..., true)` | Quên scope → 0 dòng (fail-closed), không phải tất cả |

## Kiểm chứng — không tin bộ test xanh ngay lần đầu

Đã cố tình phá từng lớp để xem test có bắt không:

| Phá | Test đỏ |
|---|---|
| Xoá `CREATE POLICY` | 11 |
| Bỏ `FORCE` | 1 (meta-test cấu hình) |
| `SET` thay `SET LOCAL` | 1 (test pool) |
| App chạy bằng superuser | 17 |

Thí nghiệm "bỏ FORCE" chỉ làm đỏ 1 test vì vai trò ứng dụng hiện không
phải chủ bảng — chưa khai thác được. Đó chính là giá trị của meta-test:
nó bắt rủi ro **tiềm ẩn** trước khi rủi ro đó trở thành khai thác được.

## Khi nào xét lại

- Khách yêu cầu cách ly vật lý bằng hợp đồng
- Cần backup/restore riêng từng shop
- Một shop lớn tới mức cần tài nguyên riêng
- Có yêu cầu tuân thủ bắt buộc tách dữ liệu

## Hệ quả xấu, chấp nhận có ý thức

- Mọi index phải có `shop_id` đứng đầu, nếu không sẽ không được dùng.
- Bảng mới quên bật RLS là thủng. Đã chặn bằng 3 test QUÉT TOÀN BỘ
  database (nhóm J trong `test_tenant_isolation.py`): mọi bảng phải có
  cột `shop_id`, phải bật RLS + FORCE, và phải có policy — hoặc được khai
  báo tường minh vào `BANG_KHONG_CAN_RLS` kèm lý do.
  Đã kiểm chứng: tạo bảng `orders` quên bật RLS -> CI đỏ kèm hướng dẫn sửa.
- RLS thêm chi phí kiểm tra mỗi truy vấn. Ở quy mô 50 shop không đáng kể;
  cần đo lại nếu lên hàng nghìn.
