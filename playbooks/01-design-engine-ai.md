# Playbook 01: Design Engine bằng AI cho POD

> Cách xây dựng "nhà máy design" 1 người, output 50-100 design chất lượng/tuần mà không cần biết vẽ.

---

## 1. Triết lý

Anh không phải designer. Anh là **"creative director"** — người ra brief, chọn output, hướng đầu ra. AI làm phần execution.

**4 nguyên tắc cốt lõi:**
1. **Process > Talent** — có workflow đúng, người không biết vẽ vẫn ra design bán được
2. **Quantity drives quality** — 100 design ra 5 winner. Đừng chăm chút 1 design 4h.
3. **Niche-first, style-second** — hiểu niche trước khi mở Midjourney
4. **Human touch cuối cùng** — AI cho 80%, 20% còn lại là khác biệt sống/chết

---

## 2. Tech Stack (đã tối ưu chi phí)

| Tool | Dùng cho | Chi phí/tháng | Bắt buộc? |
|------|----------|---------------|-----------|
| **Midjourney** (Standard Plan) | Illustration, artistic design | ~730k VNĐ ($30) | ✅ Core |
| **Ideogram** (Plus) | Typography, text-in-image | ~490k ($20) | ✅ Core |
| **Kittl** (Pro) | Layout, mockup, t-shirt template | ~730k ($30) | ✅ Core |
| **Recraft** (Pro) | Vector, icon, simple illustration | ~290k ($12) | Optional |
| **Remove.bg** hoặc Photoshop | Tách nền | ~240k ($10) | ✅ |
| **Creative Fabric** | Font, element, mockup bundle | ~490k ($19) | ✅ |
| **Canva Pro** | Mockup nhanh, social content | ~290k ($12) | Optional |

**Tổng tối thiểu:** ~2.7tr VNĐ/tháng. **Đầy đủ:** ~3.3tr VNĐ/tháng.

> So sánh: 1 designer full-time VN = 12-18tr/tháng. AI stack thay thế 80% công việc với 1/5 chi phí.

---

## 3. Workflow chuẩn cho 1 Design (20-40 phút/design)

```
Step 1: Research niche  →  3-5 phút
Step 2: Concept brief   →  2-3 phút
Step 3: AI generate     →  5-10 phút
Step 4: Select & refine →  5-10 phút
Step 5: Layout + text   →  5-10 phút (Kittl)
Step 6: Export + mockup →  3-5 phút
Step 7: QC checklist    →  2 phút
```

### Chi tiết từng bước

#### Step 1: Research niche (3-5 phút)
- Mở Everbee/Erank, filter best-sellers trong niche target
- Note 3 thứ: **concept chung**, **style đang trending**, **gap chưa ai làm**
- Screenshot 5-10 best-seller → moodboard (không copy, để hiểu "feel")

#### Step 2: Concept brief (viết ngắn, 30 giây)
Template:
```
Niche: [cat mom]
Audience: [nữ 25-45, yêu mèo, mua quà]
Mood: [funny, cozy, warm]
Style: [vintage illustration / modern flat / hand-drawn]
Color palette: [warm earthy tones]
Text hook: [tagline/pun — viết sau]
Format: [portrait t-shirt / mug wraparound / square poster]
```

#### Step 3: AI Generate
**Midjourney prompt formula chuẩn:**
```
[subject], [style keywords], [composition], [color], [mood], [technical params]
--ar 4:5 --style raw --v 6.1
```

**Prompt ví dụ thực tế (cat mom niche):**
```
Cute cartoon illustration of a cozy cat sitting in a coffee mug, vintage storybook style, warm earthy color palette, simple background, centered composition, thick outlines, t-shirt design, sticker style --ar 4:5 --no text, letters, words --style raw --v 6.1
```

**Key tricks:**
- `--no text, letters, words` → tránh AI generate chữ rác
- `--style raw` → giảm "AI look" sến súa
- Aspect ratio `4:5` cho t-shirt portrait, `1:1` cho mug/tote, `3:4` cho poster
- Tạo 4 variants → upscale 1-2 tốt nhất → rerun 8-16 lần để có pool 20+ options

#### Step 4: Select & Refine
Tiêu chí chọn 1 từ pool 20:
- [ ] Có thể hiện lên áo đen / áo trắng đều đẹp?
- [ ] Khi resize về 300x400px còn rõ?
- [ ] Không có fingers/anatomy sai của AI?
- [ ] Background có dễ tách không?

Tách nền bằng Remove.bg (free 50 lần/tháng) hoặc Photoshop.

#### Step 5: Layout + Text (Kittl)
- Import design vào Kittl template t-shirt
- Thêm text hook ở trên/dưới (Ideogram nếu cần typography đẹp)
- Font: KHÔNG dùng font Microsoft default, dùng Creative Fabric hoặc Google Fonts commercial-free

**Text hook công thức winner:**
- Pun/wordplay: "Purr-fect Mom" (cat niche)
- Proud statement: "Golden Retriever Dad Est. 2023"
- Inside joke: "My Therapist Has Fur" (pet niche)
- Custom placeholder: "[Name]'s Coffee Club"

#### Step 6: Export + Mockup
- Export PNG transparent, 300 DPI, tối thiểu 4500x5400px (Printify spec)
- Mockup bằng Kittl hoặc Placeit templates — không tự chụp

#### Step 7: QC Checklist (PRINT NÀY RA DÁN MÀN HÌNH)
- [ ] Không copy watermark sót từ moodboard
- [ ] Typography không lỗi chính tả
- [ ] Không vi phạm trademark (Google "[text] trademark" check)
- [ ] Google Lens reverse search — không match 90%+ design có sẵn
- [ ] File đúng resolution Printify require
- [ ] Mockup trên áo đen + áo trắng đều đẹp

---

## 4. Batch Processing (cách anh ra 50-100 design/tuần)

**Ngày trong tuần:**

| Thứ | Task | Output |
|-----|------|--------|
| T2 sáng | Research 5 niche, viết 25 concept brief | 25 briefs |
| T2 chiều | Midjourney generate batch 1 (12 concept) | 60-120 images |
| T3 | Select, refine, tách nền batch 1 | 20 designs ready |
| T4 sáng | Midjourney generate batch 2 (13 concept) | 65-130 images |
| T4 chiều | Select, refine batch 2 | 20 designs ready |
| T5 | Kittl layout + text cho 40 designs | 40 final designs |
| T6 | Mockup + upload Etsy/eBay | 40 listings mới |
| T7-CN | Nghỉ hoặc research niche mới | Óc sáng lại |

**Bí quyết speed:**
- Mở 4-6 concept cùng lúc trên Midjourney (parallel generation)
- Dùng `--repeat 4` để tự động tạo 4 lần 1 prompt
- Lưu template Kittl dùng lại cho nhiều design cùng style

---

## 5. Prompt Library — Cách tự xây dựng

**Tổ chức Notion database:**

```
Table: Prompt Library
Columns:
- Niche (cat, dog, teacher, nurse, gym...)
- Style (vintage, flat, hand-drawn, realistic, boho...)
- Product type (tee, mug, poster, tote)
- Base prompt (full text)
- Winner? (yes/no — mark khi design bán được)
- ROI rank (1-5)
```

Mỗi lần có winner → save prompt variant vào library → lần sau tái sử dụng 80%, đổi 20%.

**Sau 6 tháng** anh sẽ có **200-500 prompts proven**. Đây là **tài sản không ai copy được**, vì nó match với khẩu vị audience của anh.

---

## 6. Nguồn học Prompt Engineering cho POD (miễn phí/rẻ)

1. **YouTube channels:**
   - "Greg Gottfried" — POD + AI design
   - "Detour Shirts" — t-shirt business workflow
   - "Cassiy Johnson" — Etsy POD với AI

2. **Skool community:**
   - "POD Designs" (có free tier)

3. **Reddit:** r/midjourney, r/printondemand — tìm "prompt for t-shirt"

4. **Midjourney Showcase** (showcase.midjourney.com) — copy prompt winners, modify cho niche của anh

---

## 7. Phân bổ portfolio 🟡/🟢 (link với IP risk)

Anh đang ở medium risk. Design engine mới phải đẩy dần sang low risk:

| Tháng | 🟡 Medium (AI modify 70%) | 🟢 Low (AI generate original) |
|-------|---------------------------|------------------------------|
| 1-3 | 80% output | 20% output |
| 4-6 | 60% | 40% |
| 7-12 | 40% | 60% |
| 13+ | 20% | 80% |

**Quy tắc 🟢 "Original":** Prompt viết ra KHÔNG reference bất kỳ design Etsy nào. Research bằng **keyword + data**, không phải bằng screenshot best-seller.

---

## 8. KPI để đo Design Engine có hoạt động

Weekly:
- **Output:** 40-50 design hoàn thành / tuần (Phase 1), 60-80 (Phase 2+)
- **Time/design:** giảm từ 40 phút → 20 phút sau 3 tháng luyện
- **Winner rate:** 1 design bán ≥ 5 đơn trong 30 ngày = "winner". Target: 5-10% designs là winner.
- **Cost/winner:** tool cost + time cost ÷ số winner. Target: < 200k/winner sau 6 tháng.

---

## 9. 10 sai lầm thường gặp (anh tránh = tiết kiệm 3 tháng)

1. **Chăm chút 1 design 2 giờ** — AI POD là game số lượng, không phải studio
2. **Dùng Canva để design chính** — Canva tốt cho mockup, tệ cho original design
3. **Không tách nền** — design có nền trắng cháy trên áo đen = thất bại
4. **Resolution thấp** — Printify reject < 300 DPI, mất công làm lại
5. **Font không commercial** — bị DMCA từ font foundry (ít gặp nhưng có)
6. **Bỏ qua Google Lens check** — upload design y hệt 1 best-seller có sẵn
7. **Không save prompt winner** — lần sau không reproduce được
8. **Prompt quá dài, quá specific** — AI confuse, output tệ
9. **Dùng 1 style duy nhất** — portfolio đơn điệu, khó scale sang niche mới
10. **Không test A/B mockup** — listing dùng mockup tệ, CTR thấp mà không biết

---

## 10. Chuyển từ cá nhân → giao VA (Phase 2, tháng 5+)

Khi đã thành thạo workflow, anh có thể giao phần nào cho VA:

| Task | Anh làm | VA làm |
|------|---------|--------|
| Research niche + brief | ✅ | ❌ (cần óc business) |
| Midjourney generate | Setup prompt | ✅ Chạy batch |
| Select tốt nhất | ✅ Quyết định cuối | VA shortlist 5 options |
| Tách nền, refine | ❌ | ✅ |
| Kittl layout + text | Approve design cuối | ✅ Setup |
| Mockup + export | ❌ | ✅ |
| Upload listing | ❌ | ✅ |

Anh chỉ giữ 2 bước quan trọng nhất: **brief đầu vào** và **approve đầu ra**. Mỗi bước mất 5 phút/design. 50 design/tuần = 4-5h/tuần thay vì 30h.

---

## 11. Action items cho 30 ngày tới

**Tuần 1:** Setup stack (Midjourney, Ideogram, Kittl, Creative Fabric) — 3.3tr
**Tuần 2:** Làm theo workflow 20 designs đầu — đo time/design
**Tuần 3:** Build Notion Prompt Library, log 10 prompt đầu
**Tuần 4:** Mục tiêu 50 designs output, đánh giá winner rate sau 4 tuần

Xong tháng 1 anh sẽ biết **engine có chạy không**, trước khi scale lên tháng 2-3.
