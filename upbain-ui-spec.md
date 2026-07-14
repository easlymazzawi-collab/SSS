# UpBain Control — UI Specification (Complete)

> Tài liệu mô tả đầy đủ toàn bộ giao diện, layout, component, form field, hành vi tương tác và data state của UpBain Control. AI có thể dùng tài liệu này để thiết kế lại giao diện theo bất kỳ style nào mà không cần nhìn code gốc.

---

## 1. Tổng quan

- **Loại:** Web SPA (Single-Page Application), admin dashboard
- **Người dùng:** 1 admin (local-first), có thể mở rộng multi-user
- **Ngôn ngữ UI:** Tiếng Việt
- **Theme gốc:** Dark (GitHub-inspired dark palette)
- **Icon set:** Lucide Icons (stroke icons)

---

## 2. Layout tổng thể

```
┌─────────────────────────────────────────────────────────┐
│  TOPBAR (sticky, height ~56px)                           │
│  [Logo] [Tên trang]  [spacer]  [Status] [Thử lại] [START] [STOP] │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│   SIDEBAR    │         CONTENT AREA                     │
│   248px      │         (scroll độc lập)                 │
│   (sticky    │                                          │
│   full       │                                          │
│   height)    │                                          │
│              │                                          │
│  [Tìm nhanh] │                                          │
│  [Account]   │                                          │
└──────────────┴──────────────────────────────────────────┘
```

- Mobile (<768px): Sidebar ẩn, hamburger → drawer overlay
- Grid system: 12 cột, gap 16px

---

## 3. Màn hình đăng nhập

**Hiển thị:** Overlay fixed toàn màn hình (z-index cao nhất), backdrop blur  
**Background:** Gradient tối + 2 radial glow: cyan (góc trái trên) + blue (góc phải trên)

**Card đăng nhập** (căn giữa, width min(420px, 100%)):
- Brand mark (icon gradient cyan→blue) + Tên app "UpBain Control" + subtitle
- Form:
  - Input: Tên đăng nhập (autocomplete=username)
  - Input: Mật khẩu (type=password, autocomplete=current-password)
  - Button PRIMARY full-width: "Đăng nhập"
  - Error text: màu đỏ, hiển thị inline dưới button (không alert)
- Enter key: submit form
- Button: disable + loading state khi đang request

**Auth setup banner** (hiện sau login nếu dùng mật khẩu mặc định):
- Banner cảnh báo màu amber ở đầu trang: "Bạn đang dùng mật khẩu mặc định. Đổi ngay."
- Button [✕ Đóng] góc phải

---

## 4. Sidebar

### Brand block (đầu sidebar):
- Icon mark (gradient, chữ "U" hoặc icon bot)
- Tên "UpBain" + subtitle "Control v1.0"

### Navigation (danh sách dọc, scroll):

**Nhóm chính** (không có label phân cách):

| Icon Lucide | Label | Badge | Ghi chú |
|---|---|---|---|
| layout-dashboard | Điều khiển | — | |
| megaphone | Up bài ads | Số mapping active | |
| badge-percent | Ads cuối | — | |
| workflow | Vận hành bot | — | Có subtab |
| shield | Admin bot | — | Có subtab |
| radio-tower | Kênh & folder | Số kênh | |

**Nhóm Hệ thống** (label "Hệ thống" phân cách):

| Icon Lucide | Label |
|---|---|
| calendar-clock | Lịch auto |
| user-cog | Admin userbot |
| database | Backup & dữ liệu |
| terminal | Log realtime |

### Subtab Vận hành bot (hiện dưới khi click tab):
- User của bot
- Cấu hình bot
- Kho bài đã up
- File to link
- Kho link share
- Mã xem
- Anti-flood

### Subtab Admin bot:
- Forum chung admin
- Topic quản lí từng bot
- Tiến độ up từng topic
- Mời bot vào forum
- Log hệ thống & spam

### Active states:
- Tab active: highlight background + màu accent + indicator bar 3px bên trái
- Subtab active: màu accent, no indicator bar
- Subtab list: hiển thị khi tab parent active hoặc được click, ẩn khi click tab khác

### Cuối sidebar:
- **[Tìm nhanh]** button (icon command + label + kbd "Ctrl K")
  - Border, hover: highlight accent
- **Account block:** Avatar vòng tròn (2 chữ cái đầu) + tên "Admin" + subtitle "Local dashboard"

---

## 5. Topbar

**Nội dung từ trái sang phải:**
- Logo nhỏ + Tên tab hiện tại (h1)
- spacer (flex-grow)
- Status badge (realtime)
- [Thử lại] button SECONDARY
- [START] button SUCCESS
- [STOP] button DANGER

### Status badge:
Pill shape với dot animation + text:
- `Live @username` — xanh lá (Telegram connected)
- `Runtime ON` — xanh lá (worker đang chạy)
- `No Telegram` — vàng (backend ok, TG offline)
- `Chưa kết nối` — vàng (default)
- `Backend offline` — đỏ

### START / STOP:
- START: gọi API bật worker → cập nhật badge + toast
- STOP: gọi API tắt worker + cancel jobs → toast báo số jobs đã hủy
- Cả hai: disable button trong lúc request

---

## 6. Command Palette (Ctrl+K)

**Hiển thị:** Modal overlay xuất hiện giữa màn hình khi nhấn Ctrl+K hoặc nút Tìm nhanh

**Nội dung:**
- Input search lớn ở đầu
- List kết quả: tên tab/subpage, icon, mô tả ngắn
- Keyboard navigation: Arrow Up/Down chọn item, Enter mở, Escape đóng
- Recent actions: hiện các tab vừa truy cập

---

## 7. Tab: Điều khiển (Dashboard)

### Auth setup banner (conditional):
- Hiện nếu đang dùng mật khẩu mặc định
- Màu amber, có nút đóng

### Stats row (4 card):
| Card | Value | Subtitle |
|---|---|---|
| Userbot | Connected/Offline | Trạng thái kết nối |
| Auto | Running/Stopped/Armed | Worker state |
| Mapping | Số mapping | Topic đã cấu hình |
| Kênh đích | Số kênh | Registry kênh |

### Panel: Issues (System warnings):
- List cảnh báo hệ thống (kênh chết, mapping lỗi, v.v.)
- Mỗi row: icon ⚠ + mô tả issue + [Jump] (đến trang liên quan) + [Fix] (tự sửa)
- Empty state: "Không có cảnh báo"

### Panel: Kho media theo topic (7 cột):
- Header: "Kho media theo topic" + [Scan] button WARNING
- Table mỗi topic: tên topic | số bài hiện có | số bài cần | % đủ | trạng thái
- Mỗi row có button inline: [▶ Run topic] [Scan kho]
- Empty state khi chưa scan

### Panel: Máy đang chạy (5 cột):
- Header + [Refresh]
- 3 metric tiles: CPU% | RAM (used/total MB) | Disk (used/total GB)
- Nếu backend offline: hiện info box

### Panel: Jobs đang chạy (12 cột):
- Table: #ID | Loại job | Trạng thái | Progress bar + % | [Hủy]
- Liveness badge màu theo state: queued(amber), running(blue), waiting_flood(purple), succeeded(green), failed(red), cancelled(muted)
- Empty state: "Không có job nào đang chạy ✓"

---

## 8. Tab: Up bài ads (Topics/Mappings)

### Header:
- Tiêu đề + subtitle
- [Sinh topic_map.txt] SECONDARY: download file text
- [+ Thêm mapping] PRIMARY

### Panel: Nguồn bài ads:
**Header:** "Bài ads vận hành" + [Check nguồn ads] WARNING

**Form thêm nguồn** (inline, 1 dòng):
- Input: "Link/kênh/nhóm ads" (placeholder: URL hoặc -100...)
- Button [Lưu nguồn ads] PRIMARY

**Table nguồn đã lưu** — mỗi row có:
- Tên nguồn (tự nhận từ backend) | Chat ID | Trạng thái
- [Check] button per row: probe nguồn đó
- [Xóa] button per row: confirm → xóa

### Search + Filter mappings:
- Input search: "Tìm theo tên mapping / nguồn / đích..."
- **Filter chips** (buttons toggle): Tất cả | ads | noads | ads + final | Đang bật | Tạm tắt
- [Xóa bộ lọc & tìm] button: reset search + filter
- Count text: "Đang hiển thị X/Y mapping"

### Form thêm/sửa Mapping (collapsible card):

**Grid 3 cột — Fields cơ bản:**
- Input: Nguồn (link bài bắt đầu, ID, @kênh, nhóm, topic, hoặc format `-100xxx:topicId:msgId`)
- Input: Tên hiển thị (tự nhận nếu bỏ trống)
- Input: Đích chính (ID, @kênh, link nhóm, tên kênh, /alias)

**Stack: Đích thêm** (dynamic rows):
- Mỗi row: Input placeholder "Thêm ID/kênh/nhóm/link/tên kênh" + [×] button xóa row
- Button [+ Thêm đích]: thêm row mới
- Rule: row cuối không xóa được (chỉ clear giá trị), row khác xóa được

**Grid 4 cột — Cấu hình:**
- Input number: Số media (target, vd: 30)
- Input number: Số bài (target, bỏ trống = không giới hạn)
- Input: Bài bắt đầu (link bài trong topic, msg ID, hoặc trống = dùng cursor đã lưu)
- Input: Bài cuối riêng (link/ID/kênh cho bài final ads riêng của mapping này)

**Grid 4 cột — Options:**
- Select: Chế độ (branch)
  - `ads` — trộn ads vào content
  - `noads` — không ads
  - `ads + final` — trộn ads + chạy ads cuối
- Select: Cách xếp media
  - `Tự động theo gợi ý (mặc định)` — hint mode
  - `ads trước` — zdone: ads trước, content sau
  - `ads xen` — xdone: ads xen đều
  - Preview text bên dưới: "Chọn mode để xem trước cách xếp"
- Select: Pin mode
  - `Ghim bài mới nhất`
  - `Link bài bắt đầu`
  - `Con trỏ đã lưu`
- Select: Trạng thái
  - `Bật` (active)
  - `Tạm tắt` (paused)

**Stack: Token bot** (dynamic, optional):
- Mỗi row: Input type=password placeholder "123456:ABC..." + [×]
- Button [+ Thêm token bot]: thêm token bot riêng cho mapping này
- Label: "Token bot (tùy chọn)"

**Input: Kênh bắt buộc tham gia bot:**
- "@kenh_bat_buoc hoặc -100... · trống = dùng kênh global"

**Footer form:** [Lưu mapping] SUCCESS | [Hủy] GHOST

### Danh sách Mappings:

**Mỗi mapping = 1 card collapsible:**

*Header (luôn hiển thị, clickable để expand/collapse):*
- Tên mapping (bold)
- Badge: branch (ads/noads/ads+final)
- Badge: trạng thái (Bật/Tạm tắt)
- Chat ID nguồn (code style)
- Số đích
- Buttons góc phải: [▶ Chạy] SUCCESS | [Xóa] DANGER (với confirm + undo)

*Body (chỉ khi expanded):*
- Form sửa đầy đủ như form thêm mới
- **Autosave:** input thay đổi → tự động save sau debounce (không cần bấm Save)

**Undo banner** (hiện sau khi xóa, timed):
- Text: "Đã xóa mapping [tên]"
- [Hoàn tác] button: khôi phục
- [×] button: đóng banner, xác nhận xóa vĩnh viễn
- Tự đóng sau N giây

---

## 9. Tab: Ads cuối (Alltask)

### Header: "Ads cuối phiên" + [Chạy ads cuối] SUCCESS

### Panel trái (5 cột) — Cấu hình:
- Toggle: "Bật ads cuối"
- Info block khi bật: "Kết thúc task — Up xong là hoàn tất task"
- Input: "Nguồn ads cuối" (link/chat/topic/msg ID)
- **Parse hint** bên dưới input: hiển thị kết quả parse: "chat -100xxx · topic 5 · msg 678"
- Radio group "Cách lấy nguồn":
  - `Lấy toàn bộ nguồn` — lấy mọi bài trong kênh/topic
  - `Chỉ bài được nhập` — chỉ bài cụ thể đó
  - Hint text thay đổi theo lựa chọn
- **Kênh ads đích:**
  - Header + [Chọn tất cả] + [Bỏ chọn]
  - Checkbox list: mỗi kênh registry (có thể scroll)
  - Hint count: "X kênh đã chọn"
- Button [Lưu ads cuối] PRIMARY

### Panel phải (7 cột) — Lịch sử:
- Lần chạy gần nhất: thời gian, số bài gửi, kết quả
- Empty state: "Chưa chạy lần nào"

---

## 10. Tab: Vận hành bot — Subtab: User của bot

### Header:
- Tiêu đề
- Select filter bot (Tất cả / từng bot)
- Input search: "Tìm ID, @username hoặc tên bot..."
- [Xuất TXT] button: download danh sách user

### Stats row (4 card nhỏ):
- Tổng user | Premium users | Số ngôn ngữ | Bot đang lọc

### Table users:
| Avatar | ID | Username | Tên | Premium ★ | Ngôn ngữ | Lần cuối | Actions |
|--------|-----|---------|-----|---------|---------|----------|---------|
- [Xem chi tiết] per row → mở **detail panel** slide-in từ phải
- [Chặn/Bỏ chặn] per row → toggle + badge

**Detail panel (slide-in hoặc modal):**
- Avatar lớn + tên + ID + username
- Lịch sử tương tác: lần đầu, lần cuối, số lần dùng
- Tags: Premium, ngôn ngữ
- [Đóng] button (cả nút và Escape)

### Leaderboard panel:
- Header: "Bảng xếp hạng tháng" + [Lưu top tháng & reset] + hint "Tháng hiện tại: MM/YYYY · X lượt chốt trước đó"
- Table: #rank | User | Bot | Invites | Clicks | Điểm | [Broadcast riêng] [Chi tiết]
- **Lịch sử tháng** section: danh sách snapshot đã chốt: Tháng | Lưu lúc | Top 3 summary | Badge "top 3"

### Top views panel:
- Table: #rank | Tên link/bài | Nguồn | Ngày | Token | Views | [Xem] [Share]

---

## 11. Tab: Vận hành bot — Subtab: Cấu hình bot

### Header: "Cấu hình bot" + [Lưu cấu hình bot] PRIMARY

### Grid module cards (2 cột):

**Module 1: Xem lại bài cũ (Archive)**
- Header: icon archive + "Xem lại bài cũ" + Toggle ON/OFF
- Body:
  - Checkbox: "Trộn ads"
  - Input number: "Tự xoá sau N phút" (0 = không xoá)
  - Textarea: "Caption thông báo" (hỗ trợ placeholder `{time}`)

**Module 2: File to link**
- Header: icon link + "File to link" + Toggle ON/OFF
- Body:
  - Checkbox: "Protect content"
  - Checkbox: "Cho phép forward"
  - Input number: "Giới hạn xem" (0 = không giới hạn)
  - Input number: "Tự xoá sau N phút" (0 = không xoá)
  - Textarea: "Caption thông báo"

**Module 3: Force join kênh**
- Header: icon users + "Force join kênh" + Toggle ON/OFF
- Body:
  - Input: "Kênh bắt buộc tham gia" (@username hoặc -100...)
  - Textarea: "Tin nhắn khi chưa join"

**Module 4: Broadcast**
- Header: icon zap + "Broadcast" + Toggle ON/OFF
- Body:
  - Input number: "Tốc độ gửi (msg/giây)" (1–30)
  - Checkbox: "Chỉ gửi user Premium"

**Module 5: Self-delete** (tự xóa bài sau khi xem)
- Header: icon trash + "Tự xóa bài" + Toggle ON/OFF
- Body:
  - List các task self-delete: text | thời gian | [Sửa] [Xóa]
  - Inline editor khi sửa: input text + [Lưu] [Hủy]

---

## 12. Tab: Vận hành bot — Subtab: Kho bài đã up (Archive)

### Header:
- Tiêu đề
- Input search
- Date picker
- Select filter branch (Tất cả / ads / noads)
- [Làm mới] SECONDARY

### Table archive:
| Thumbnail | Caption/Tên | Bot | Thời gian | Nhánh | Actions |
|-----------|-------------|-----|----------|-------|---------|
- [Xem] per row → modal preview
- [Share] per row → copy deep-link vào clipboard
- [Bot] per row → navigate đến tab bot

**Modal preview:**
- Thumbnail lớn
- Caption đầy đủ
- Link chia sẻ + [Copy]
- Button [Đóng] (nút + backdrop click + Escape)

---

## 13. Tab: Vận hành bot — Subtab: File to link

### Bố cục: grid 12 cột, 3 card stack

**Card 1: Tạo link** (span-12):
- Header: "Tạo link" + mô tả
- **Checkbox: "Chèn link vào caption"** — bật thì bot gắn link bên dưới caption khi tạo link
- **Textarea: "Link chèn vào caption"** (hiện khi checkbox bật) — paste link bài (t.me/c/...)
- [Tạo file link] SUCCESS button
- Hint text kết quả bên cạnh button

**Card 2: Backup media user về forum** (span-12):
- Header: "Backup media user về forum"
- **Status pill ON/OFF** + mô tả trạng thái
- Toggle: "Backup media về forum"
- **Khi bật, hiện config thêm:**
  - Notice box WARN: "Bật lên thì forum đồng bộ 2 chiều với Admin bot → Mời bot vào forum"
  - Input: "Forum lưu trữ media" (ID hoặc link forum)
    - Hint + **Sync state indicator** ("— chưa đồng bộ —" hoặc "✓ đã đồng bộ")
    - Field này sync 2 chiều với field forum ở Admin bot → Mời bot
  - Checkbox: "Một topic mỗi user" — tái sử dụng topic cũ, không tạo mới mỗi lần
  - Checkbox: "Giữ caption gốc của user khi forward vào topic"
  - Notice box INFO: hướng dẫn mời bot vào forum
  - [Lưu cấu hình backup] PRIMARY | [Kiểm tra quyền bot] SECONDARY (→ navigate đến Admin bot/Invite)

**Card 3: Link đã share** (span-12):
- Header: "Link đã share" + mô tả + [Mở kho link share →] button
- Mini table: 5 link mới nhất (token | owner | views | trạng thái | [thu gọn/bung])
- Mỗi row collapsible: thu gọn → hiện thêm: expiry, actions [Sửa owner] [Xóa] [Xem lại/Revive]
  - [Sửa owner]: prompt → đổi tên owner trong local data
  - [Xóa]: confirm → xóa link
  - [Xem lại/Revive]: gia hạn / kích hoạt lại link đã expired

---

## 14. Tab: Vận hành bot — Subtab: Kho link share

### Header: "Kho link share" + [← Quay lại File to link] button

### Filter bar (4 cột):
- Input search: "Tìm theo tên user / token" (placeholder: @minhvip, fl_a8d3e0...)
- Select "Trạng thái": Tất cả | active | expired
- Select "Sắp xếp": Mới nhất | Cũ nhất | Mở nhiều
- [Làm mới] button

### Table đầy đủ:
| Token | Owner/User | Caption | Views | Hết hạn | Trạng thái | Actions |
|-------|-----------|---------|-------|---------|-----------|---------|
- Row expired: dim/strikethrough
- [Sửa owner] | [Xóa] | [Revive] per row

### User summary section (bên dưới table):
- Hiện khi search theo user: tổng link, tổng views, link active/expired

---

## 15. Tab: Vận hành bot — Subtab: Mã xem (View codes)

### Collapsible config card (collapse toggle ở header):

**Select: Loại nội dung** (config khác nhau cho từng loại):
- `Mặc định (fallback mọi loại)`
- `Xem bài hôm nay`
- `Xem bài cũ`
- `File to link`
- `Broadcast`

**Grid 3 cột:**
- Input: Prefix mã (vd: "vnkong", max 16 ký tự)
- Input number: Độ dài suffix (min) (3–16)
- Input number: Độ dài suffix (max) (3–16)

**Grid 2 cột:**
- Input number: Hạn (phút, 0 = vô hạn)
- Input number: Auto-delete sau (phút, 0 = không xóa)

- Checkbox: "Tự xoá nội dung sau khi xem"
- Input: "Caption kèm mã (tuỳ chọn)" (max 256 ký tự)
- [Lưu cấu hình] PRIMARY + hint "Áp dụng cho mã mới của loại đang chọn"

### Danh sách mã đang hiệu lực:
- Header + [Làm mới] + hint count
- Table: Mã | Loại | Hạn | Views | [Xóa] (confirm)

---

## 16. Tab: Vận hành bot — Subtab: Anti-flood

### Header: "Anti-flood center" + [▶ Chạy mô phỏng] SUCCESS | [■ Dừng] DANGER

### Form tham số (3 cột):
- Select "Chiến lược gửi":
  - `Sequential` — gửi từng cái một
  - `Batch + delay` — gom nhóm + nghỉ giữa batch
  - `Queue + semaphore` — worker pool
- Input number: Số bài mô phỏng (5–200)
- Input number: Concurrency (1–10, cho Queue)
- Input number: Batch size (2–20, cho Batch)
- Input number: Delay giữa item (ms)
- Input number: Delay giữa batch (ms)

### Stats card (5 counter):
- **Sent** | **Failed** | **Rate-limited** | **Tổng chờ (giây)** | **Đã xử lý (X/Y)**

### Progress bar (0–100%)

### Terminal log (scrollable, monospace)

### Checklist chống flood (static list):
- `flood_sleep_threshold = 86400` · Telethon auto-sleep [link docs]
- `sleep_threshold ≥ 120s` · Pyrogram [link docs]
- `max_concurrent_transmissions ≤ 3`
- `Chunk upload ≤ 20 MB`
- `Idempotent retry`
- `Buffer +5s khi sleep`
- `Gửi theo batch (5–10 bài, nghỉ 1–2s giữa batch)`
- `Track lỗi flood (vẽ chart theo bot/topic)`

---

## 17. Tab: Admin bot — Subtab: Forum chung admin

### Bố cục 2 panel:

**Panel trái — Cấu hình:**
- Input: Forum Chat ID (-100...)
- Input number: Root topic ID
- Toggle: "Tự tạo topic cho bot khi START"
- Toggle: "Mời bot vào forum chung"
- Toggle: "Auto pin link ngày mai"
- [Lưu forum chung] PRIMARY

**Panel phải — Trạng thái:**
- Trạng thái kết nối forum (live check)
- Danh sách bot đã vào forum + quyền
- Info box nếu chưa cấu hình

---

## 18. Tab: Admin bot — Subtab: Topic quản lí từng bot

**Table:**
| Bot | Topic ID | Tên topic | Loại | Actions |
|-----|---------|----------|------|---------|
- [Link] per row: copy link topic
- [Mở topic] per row: navigate đến topic
- Empty state khi chưa load

---

## 19. Tab: Admin bot — Subtab: Tiến độ up từng topic

### Header + [Refresh tiến độ] SECONDARY

**Table:**
| Topic nguồn | Topic đích | Bài hiện tại | Bài kế tiếp | % | Cập nhật lúc | Actions |
|------------|-----------|-------------|------------|---|------------|---------|
- Progress bar inline trong cell %
- [Thông báo] per row: gửi thông báo về forum
- [Mở cursor] per row: jump đến vị trí cursor

---

## 20. Tab: Admin bot — Subtab: Mời bot vào forum

### Bố cục 2 panel:

**Panel trái — Forum mời bot (chung):**
- Tiêu đề + note: "đồng bộ 2 chiều với File to link → Backup media về forum"
- Input: "ID / Link forum" (-100... hoặc t.me/+xxx)
  - **Sync state indicator** bên dưới: "— chưa đồng bộ —" / "✓ đã đồng bộ với File to link"
  - Field này sync 2 chiều với field forum ở File to link
- Hint: quyền bot cần thiết (Manage topics + Send media)
- [Lưu forum mời bot] PRIMARY + hint text kết quả

**Panel phải — Danh sách bot:**
- Table: Tên bot | @Username | Quyền | Trạng thái | [Mời] [Check]
- [Mời] per row: thêm bot vào forum
- [Check] per row: kiểm tra quyền hiện tại bot trong forum
- Empty state khi chưa có bot

---

## 21. Tab: Admin bot — Subtab: Log hệ thống & spam

- Terminal-style hoặc table
- Mỗi entry: thời gian | loại log | nội dung
- Loại: spam alert | copy album error | permission loss | metadata update
- Filter theo loại
- Auto-scroll khi có log mới
- [Mở log] button per row: xem chi tiết đầy đủ

---

## 22. Tab: Kênh & folder

### Header + toolbar:
- [+ Thêm kênh] PRIMARY → modal
- [Load ảnh + tên kênh] SECONDARY: sync metadata từ Telegram cho tất cả kênh
- [Sync folder] SECONDARY: import folder từ Telegram
- [Check kênh chết] WARNING: probe liveness tất cả kênh
- [Xóa kênh chết] DANGER: confirm → xóa tất cả kênh dead

### Panel chính — Danh sách kênh:
- Count: "X kênh · Y ads · Z không ads"
- Search input: tìm theo id, tên, alias, @username

**Table kênh:**
| Avatar | Chat ID | Tên | @Username | Alias | Loại | Liveness | Actions |
|--------|---------|-----|----------|-------|------|---------|---------|

**Liveness badges:**
- `alive` → xanh
- `dead` → đỏ
- `no_access` → vàng (không tự xóa — chỉ không có quyền)
- `unknown` → muted

**Per-row actions:**
- [Load ảnh+tên] (icon sync): sync metadata kênh đó từ Telegram
- [Xóa khỏi pool] DANGER: confirm → soft-delete kênh khỏi registry

### Panel: Kênh chết (đã đánh dấu):
**Table:**
| Chat ID | Tên (nếu biết) | Lần check | Lý do | Actions |
|---------|--------------|----------|-------|---------|
**Per-row actions (3 buttons):**
- [Xóa khỏi pool]: gỡ khỏi registry
- [Gỡ khỏi mapping]: gỡ ID khỏi tất cả destinations trong mappings liên quan
- [Xóa khỏi danh sách die]: chỉ xóa khỏi list kênh chết (không xóa khỏi registry)

### Modal: Thêm kênh:
- Input: "Link / ID / username / addlist"
  - Chấp nhận mọi định dạng: @username, https://t.me/..., -100xxx, link addlist folder
- Hint text: "Nhập mọi định dạng — tự nhận diện"
- Nút Hủy + OK

---

## 23. Tab: Lịch auto

### Bố cục 2 panel:

**Panel trái (4 cột) — Cấu hình chung:**
- Toggle: "Bật lịch auto"
- Input time: Giờ chạy (HH:MM)
- Select: Timezone (Asia/Bangkok, Asia/Ho_Chi_Minh, UTC)
- Select: Chu kỳ lặp (Một lần trong ngày / Mỗi 6 giờ / Mỗi 3 giờ / Mỗi giờ)
- Toggle: "Chỉ chạy khi đã START"
- Toggle: "Dừng nếu thiếu media bắt buộc"
- [Lưu lịch] PRIMARY

**Panel phải (8 cột) — Phân luồng chạy:**
- Subtitle: "Kéo thả để đổi bước nào chạy trước"
- **Drag-and-drop list** — mỗi item:
  - Icon grip (handle kéo thả)
  - Số thứ tự + tên bước
  - Meta: số mapping/bot
  - Toggle bật/tắt bước này riêng
- Thứ tự mặc định: Up bài ads → Ads cuối → Archive bot → Backup dữ liệu

---

## 24. Tab: Admin userbot

### Header:
- Tiêu đề + subtitle
- [Lưu cấu hình hash] PRIMARY (ở header section)

### Panel trái (7 cột) — Đăng nhập userbot:

**Status block:**
- Info box: "Trạng thái đăng nhập"
- Badge trạng thái:
  - "Đã có session" → badge xanh
  - "Chưa đăng nhập" → badge muted
  - "Đang chờ OTP" → badge amber

**Khi đã đăng nhập — Logged-in card:**
- Avatar icon lớn
- Tên Telegram + @username
- Số điện thoại (masked: +66•••••)
- Thời gian đăng nhập
- [Đổi tài khoản] GHOST: logout → về bước phone
- [Đăng xuất] DANGER: confirm → logout

**Khi chưa đăng nhập — Login flow:**

*Step 1 — Phone (grid):*
- Input: "Số điện thoại admin" (placeholder +84xxx, autocomplete=tel)

*Step 2 — OTP (ẩn cho đến khi gửi code thành công):*
- Input: "Mã OTP" (inputmode=numeric, autocomplete=one-time-code, max 8 ký tự)
- Hint: "Mã có hiệu lực ~5 phút — nhập xong bấm Xác nhận login ngay"

*Step 3 — 2FA (ẩn, chỉ hiện khi TG báo need password):*
- Input: "Mật khẩu 2FA" (type=password, autocomplete=current-password)
- Hint: "Tài khoản đang bật xác minh 2 bước"

**Toolbar login (bên dưới các step):**
- [Gửi mã OTP] SECONDARY: gửi OTP về phone → disabled sau khi gửi
- [Xác nhận login] SUCCESS: disabled cho đến khi có OTP/2FA
- [Đăng xuất] DANGER

**Toggles:**
- "Tự kết nối lại userbot khi mở tool"
- "Chỉ cho admin userbot đã login thao tác dữ liệu"

### Panel phải (5 cột) — Cấu hình API Hash:
- Input: API ID (số nguyên)
- Input: API Hash (32 ký tự, type=password) — lưu encrypted, không hiện lại
- Input readonly: Đường dẫn session (data/sessions/admin_userbot.session)
- Input: Device model (vd: "UpBain Admin")
- Input: App version (vd: "1.0")
- Input: Chat tạm khi cần stage (Saved Messages hoặc -100...)
- Info box: "Bot token tách riêng — Token bot, broadcast và metadata nằm ở Vận hành bot / Admin bot để thay token không mất data"

### Panel dưới (12 cột) — Bot credentials:
- Header + [+ Thêm bot] PRIMARY

**Table bot:**
| Tên bot | @Username | Token (fingerprint ...XXXX) | Validated lúc | Trạng thái | Actions |
|---------|----------|--------------------------|--------------|-----------|---------|
- [Xác thực lại] per row: gọi getMe, cập nhật username/status
- [Xóa] per row: confirm → xóa token + deactivate

**Modal: Thêm bot:**
- Input: Tên bot
- Input: Bot Token (type=password, autocomplete=new-password)
- Hint: "Token sẽ được mã hoá AES-256. Chỉ hiện fingerprint sau khi lưu."
- [Hủy] GHOST | [Xác thực & Lưu] PRIMARY

---

## 25. Tab: Backup & dữ liệu

### Header: "Backup & dữ liệu" + [Backup ngay] SECONDARY

### Panel: Import dữ liệu cũ (5 cột):
- **Dropzone** (kéo thả):
  - "Kéo file / ZIP vào đây"
  - Định dạng hỗ trợ: .env, channels.json, folders.json, topic_map.txt, topic_rr.json, *.session, auto_config.json
  - Hover: highlight border + background
- Toolbar: [Preview import] SUCCESS | [Import từ workspace] SECONDARY | [Resync disk] SECONDARY

### Panel: Lịch sử backup (7 cột):
- Header + [Làm mới]
- Table: Filename | Size | SHA256 (prefix) | Thời gian | Status | [⬇ Download]

### Panel: Lịch backup tự động (12 cột):
- Toggle: "Backup sau khi chạy lịch up bài"
- Input number: Giữ backup trong N ngày
- Input readonly: Thư mục backup
- [Lưu lịch backup] PRIMARY

### Panel: Audit log & Sandbox (12 cột):
- Header + [Bắt đầu ghi] | [Replay] | [Export JSON] | [Xoá log] DANGER

**Grid 3 cột:**
- Input number: Tốc độ replay (ms/message)
- Input readonly: Số tin đã ghi
- Input readonly: Trạng thái (idle/recording/replaying)

**Activity chart** (optional visualization):
- Bar chart hoặc stream theo thời gian
- Count badge: "X hành động"

**Audit table:**
| Thời gian | Actor | Action | Resource | Success |
|----------|-------|--------|---------|---------|

---

## 26. Tab: Log realtime

### Header:
- Tiêu đề
- **SSE status badge**: "Live" (xanh) / "Connecting..." (amber) / "Polling" (amber, REST fallback)
- [Clear logs] DANGER

### Terminal component:
- Background rất tối (#070b10)
- Decorative bar: 3 dot tròn (đỏ/vàng/xanh macOS style)
- Log area (scrollable, height 400px+):
  - Format mỗi dòng: `HH:MM:SS  [LEVEL]  message`
  - Màu level: INFO (trắng/muted) | OK (xanh) | WARN (vàng) | ERROR (đỏ)
  - Auto-scroll khi có log mới (trừ khi user đang cuộn lên)
  - Giữ tối đa ~500 dòng; cũ hơn tự xóa khỏi DOM

---

## 27. Components — Chi tiết đầy đủ

### Toast notification:
- Vị trí: bottom-right, fixed
- Stack từ dưới lên
- Animation: slideUp + fadeIn
- **Types:** success (border xanh) | error (border đỏ) | warning (border vàng) | info (border muted)
- Content: textContent (KHÔNG innerHTML để tránh XSS)
- Nút [×] đóng manual
- Auto-close: info/success 4s, error 6s
- **Toast Rich variant:** có thêm [Action button] inline (vd: "Hoàn tác") với callback

### Undo banner:
- Full-width banner xuất hiện ở đầu list sau khi xóa
- Text: "Đã xóa [tên item]"
- [Hoàn tác] button (thực hiện undo)
- [×] đóng (xác nhận xóa vĩnh viễn)
- Tự đóng sau N giây

### Modal:
- Backdrop click → đóng
- Escape → đóng
- Animation: fadeIn + scale hoặc slideUp
- Nút đóng [×] ở header
- Trap focus trong modal khi mở

### Toggle switch:
- Pill shape (width ~38px, height ~21px)
- ON: màu accent (blue-dark)
- OFF: màu muted/gray
- Smooth transition 0.2s

### Badge / Tag:
- Pill shape, nhỏ
- Màu theo semantic: blue | green | red | amber | muted | purple
- Optional: icon nhỏ trước text

### Status pill:
- Kiểu khác badge: to hơn, background màu mạnh hơn
- Dùng cho ON/OFF state rõ ràng
- Text "ON" xanh / "OFF" muted

### Collapsible card:
- Header: clickable, có chevron icon (xoay 90° khi open)
- Body: ẩn/hiện với transition
- State lưu vào localStorage

### Drag-and-drop list:
- Cursor: grab
- Handle icon (grip-vertical) ở đầu mỗi item
- Visual: shadow + opacity thấp khi đang kéo
- Drop zone highlight

### Stat card:
- Label nhỏ trên (font-size 12px, uppercase, muted)
- Value lớn giữa (font-size 24px, bold)
- Subtitle nhỏ dưới (font-size 12px, muted)
- Icon ở góc phải (24px, background nhẹ)

### Notice box:
- Types: warn (amber background + icon alert-triangle) | info (blue background + icon info)
- Dùng để cảnh báo quan trọng trong form (không phải toast)
- Inline trong panel/card

### Sync state indicator:
- Text nhỏ inline dưới input
- States: "— chưa đồng bộ —" (muted) | "✓ đã đồng bộ" (xanh)
- Khi field A thay đổi → field B cập nhật tự động → indicator hiện "đồng bộ"

### Progress bar:
- Height 4–5px
- Fill: màu blue, transition smooth
- Có thể có label % bên cạnh

### Run note / Info box:
- Background màu nhạt (blue-soft, amber-soft, green-soft)
- Border mờ cùng màu
- Bold label + nội dung text
- Dùng để giải thích trạng thái hoặc hướng dẫn

### Destination stack:
- Dynamic list rows
- Mỗi row: input + [×] button
- Row cuối: [×] chỉ clear giá trị, không xóa row
- Các row khác: [×] xóa row hoàn toàn
- Button [+ Thêm ...] bên dưới

### Parse hint:
- Text nhỏ bên dưới input khi nhập link Telegram
- Realtime parse: "chat -100xxx · topic 5 · msg 678"
- Màu muted khi chưa nhận diện, màu blue khi parse thành công

---

## 28. Hành vi tương tác quan trọng

### Navigation:
- Tab switch: instant, không reload trang
- URL hash: cập nhật #dashboard, #topics, v.v.
- Active tab + active subtab: persist qua localStorage (preference only)
- Subtab: chỉ hiện/ẩn panel trong cùng section

### Forms:
- Validation client-side trước submit
- Button: disable + loading spinner khi đang request
- Reset form sau submit thành công
- Error: hiện inline, không alert()

### Autosave (mapping):
- Input change trong mapping card expanded → debounce 800ms → auto-save
- Visual indicator: subtle flash hoặc "Đã lưu" text nhỏ

### Destructive actions:
- Confirm modal với mô tả hành động
- Label nút confirm = tên hành động (không chỉ "OK")
- Cancel luôn là option

### Login flow userbot (multi-step):
1. Nhập phone → [Gửi mã OTP]
2. Input OTP hiện ra → [Xác nhận login]
3. Nếu 2FA → Input 2FA hiện → [Xác nhận login]
4. Thành công → ẩn form, hiện logged-in card
5. [Đăng xuất] → confirm → reset về bước 1
6. [Đổi tài khoản] → silent logout → reset về bước 1

### Job progress (SSE realtime):
1. Tạo job → progress bar hiện trong mapping card
2. SSE event → cập nhật phần trăm + text live
3. Khi xong → toast thông báo + ẩn/freeze progress
4. [Hủy] button trong dashboard jobs panel hoặc inline

### Channel liveness:
- alive ✓ xanh
- dead ✗ đỏ — đưa vào panel "Kênh chết"
- no_access ⚠ vàng — không tự xóa (chỉ không có quyền, không chắc chết)
- unknown ─ muted — chưa check hoặc check lỗi

### 2-way sync Forum:
- File-to-link panel input forum ↔ Admin bot/Mời bot panel input forum
- Khi thay đổi một bên → bên kia cập nhật live
- Sync state indicator hiển thị real-time

### Keyboard shortcuts:
- `Ctrl+K`: mở command palette
- `Escape`: đóng modal/palette/slide-panel
- `Arrow Up/Down` trong palette: di chuyển item
- `Enter` trong palette: chọn item

---

## 29. Data states — mọi list

| State | Hiển thị |
|-------|---------|
| Loading | Spinner hoặc skeleton rows |
| Empty | Icon lớn + tiêu đề + subtitle hướng dẫn hành động |
| Data | Content bình thường |
| Error | Icon ⚠ + message lỗi + [Thử lại] button |

---

## 30. Responsive

| Breakpoint | Layout |
|---|---|
| ≥1280px | Sidebar 248px + main area, grid 12 cột |
| 768–1279px | Sidebar thu hoặc icon-only, grid 6 cột |
| <768px | Sidebar ẩn + hamburger → drawer overlay; grid 1 cột (full width) |

---

## 31. Thứ tự ưu tiên khi thiết kế lại

1. Đủ **10 tab + subtab** (cấu trúc navigation)
2. Đủ mọi **form field** (inputs, selects, toggles, checkboxes)
3. Đủ mọi **buttons** (kể cả per-row actions)
4. Đủ **4 data states** (loading/empty/data/error)
5. Navigation hoạt động (tab switch + subtab + hash)
6. Toast + Modal confirm
7. Collapsible cards + Drag-drop
8. Undo banner + Parse hint
9. Sync state indicator
10. Sau cùng: style/theme/animation

---

*Với tài liệu này, AI có thể thiết kế lại UpBain Control hoàn toàn bằng bất kỳ stack và design system nào.*
