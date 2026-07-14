# UpBain Control — UI Specification

> Tài liệu này mô tả đầy đủ toàn bộ giao diện, tính năng, layout và hành vi tương tác của UpBain Control Dashboard. AI có thể dùng tài liệu này để thiết kế lại giao diện theo bất kỳ style nào (SaaS, mobile-first, light theme, v.v.) mà giữ nguyên đầy đủ tính năng.

---

## 1. Tổng quan ứng dụng

**Loại:** Web admin dashboard, single-page application (SPA)  
**Người dùng:** 1 admin duy nhất (local-first)  
**Mục đích:** Quản lý việc forward bài Telegram từ kênh nguồn → kênh đích, điều khiển bot, xem log realtime  
**Ngôn ngữ:** Tiếng Việt  
**Theme gốc:** Dark (GitHub-inspired), có thể thiết kế lại bất kỳ theme nào  

---

## 2. Cấu trúc layout tổng thể

```
┌─────────────────────────────────────────────────────────┐
│  TOPBAR (sticky)                                         │
│  [Logo] [Tên trang]    [Status badge] [START] [STOP]    │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│   SIDEBAR    │         NỘI DUNG SECTION                 │
│   (sticky)   │         (scroll độc lập)                 │
│              │                                          │
│  Navigation  │                                          │
│  items       │                                          │
│              │                                          │
│  [Tìm nhanh] │                                          │
│  [Account]   │                                          │
└──────────────┴──────────────────────────────────────────┘
```

- Sidebar width: ~248px, sticky toàn chiều cao
- Main area: chiếm phần còn lại, scroll độc lập
- Topbar height: ~56px, sticky trên cùng của main area
- Trên mobile: sidebar ẩn, có nút hamburger mở drawer

---

## 3. Màn hình đăng nhập

**Hiển thị:** Overlay toàn màn hình khi chưa đăng nhập (z-index cao nhất)  
**Background:** Gradient tối với hiệu ứng radial glow màu cyan + blue  

**Card đăng nhập** (căn giữa màn hình, width ~420px):
- Logo/brand mark (icon hoặc chữ "U")
- Tên app: "UpBain Control"
- Subtitle: "Đăng nhập để quản trị hệ thống"
- Form:
  - Input: Tên đăng nhập (autocomplete: username)
  - Input: Mật khẩu (type=password, autocomplete: current-password)
  - Button PRIMARY: "Đăng nhập" (full width)
  - Hiển thị lỗi nếu sai credentials (text màu đỏ, không alert)
- Hành vi: Enter key submit form, disable button khi đang loading

---

## 4. Sidebar Navigation

### Brand/Logo (phần đầu sidebar)
- Icon brand + tên "UpBain" + subtitle "Control v1.0"

### Navigation items (danh sách dọc)

**Nhóm chính:**

| Icon | Label | Badge | Ghi chú |
|------|-------|-------|---------|
| layout-dashboard | Điều khiển | — | Tab dashboard |
| megaphone | Up bài ads | Số mapping | Tab topics |
| badge-percent | Ads cuối | — | Tab alltask |
| workflow | Vận hành bot | — | Tab botops, có subtab |
| shield | Admin bot | — | Tab botadmin, có subtab |
| radio-tower | Kênh & folder | Số kênh | Tab channels |

**Nhóm Hệ thống** (có label phân cách):

| Icon | Label | Ghi chú |
|------|-------|---------|
| calendar-clock | Lịch auto | Tab schedule |
| user-cog | Admin userbot | Tab telegram |
| database | Backup & dữ liệu | Tab import |
| terminal | Log realtime | Tab logs |

### Subtab của "Vận hành bot":
Hiện ra bên dưới khi click vào Vận hành bot:
- User của bot
- Cấu hình bot
- Kho bài đã up
- File to link
- Kho link share
- Mã xem
- Anti-flood

### Subtab của "Admin bot":
- Forum chung admin
- Topic quản lí từng bot
- Tiến độ up từng topic
- Mời bot vào forum
- Log hệ thống & spam

### Phần dưới sidebar:
- **Tìm nhanh** button (shortcut Ctrl+K): mở command palette
- **Account block**: Avatar + tên "Admin" + subtitle "Local dashboard"

### Trạng thái active:
- Tab đang chọn: highlight background + màu accent + indicator bar bên trái
- Subtab đang chọn: màu accent

---

## 5. Topbar

**Bố cục:** Logo nhỏ + tên trang | spacer | status badge | [Thử lại] | [START] [STOP]

### Status badge (realtime indicator):
- Dot animation + text trạng thái
- States:
  - `Live @username` — màu xanh lá (connected)
  - `No Telegram` — màu vàng (backend ok, TG offline)
  - `Backend offline` — màu đỏ
  - `Runtime ON` — màu xanh lá khi START
  - `Runtime OFF` — màu vàng khi STOP

### Buttons topbar:
- **[Thử lại]** SECONDARY: reload health check
- **[START]** SUCCESS/GREEN: bật runtime worker
- **[STOP]** DANGER/RED: dừng tất cả jobs đang chạy

---

## 6. Tab: Điều khiển (Dashboard)

### Stats cards (4 card hàng ngang):
1. **Userbot** — trạng thái kết nối (Connected/Offline)
2. **Auto** — trạng thái worker (Running/Stopped/Armed)
3. **Mapping** — số mapping đã cấu hình
4. **Kênh đích** — số kênh trong registry

### Panel: Kho media theo topic
- Header: "Kho media theo topic" + button [Scan]
- Table/list hiển thị từng topic: tên, số bài, trạng thái
- Empty state: "Chưa có dữ liệu — Bấm Scan"

### Panel: Máy đang chạy
- Header: "Máy đang chạy" + button [Refresh]
- 3 metrics: CPU%, RAM MB, Disk GB
- Nếu backend offline: hiện thông báo

### Panel: Jobs đang chạy
- Table: ID, loại job, trạng thái, progress bar, button [Hủy]
- Empty state: "Không có job nào đang chạy"
- Progress bar hiển thị phần trăm realtime qua SSE

---

## 7. Tab: Up bài ads (Topics / Mappings)

### Header section:
- Title: "Up bài ads / không ads"
- Subtitle: mô tả
- Buttons: [Sinh topic_map.txt] [+ Thêm mapping]

### Panel: Nguồn bài ads
- Form inline: Input "Link/kênh/nhóm ads" + Button [Lưu nguồn ads]
- Nút [Check nguồn ads]: probe tất cả nguồn đang có
- Table dưới: danh sách nguồn ads đã lưu (tên, ID, button xóa)

### Form thêm/sửa Mapping (ẩn/hiện toggle):
Card collapsible với:

**Grid 2 cột:**
- Input: Tên mapping (vd: "vitamin → pro")
- Input number: Chat ID nguồn (vd: -1001234567890)
- Input number: Topic ID nguồn (optional)
- Select: Chế độ ads
  - `normal` — xen đều giữa content
  - `xdone` — ads giữa
  - `zdone` — ads trước, content sau

**Kênh đích (dynamic):**
- Danh sách rows: [Input Chat ID] [Input Topic ID] [Nút xóa]
- Button [+ Thêm đích] để thêm row mới

**Footer form:** [Hủy] [Lưu mapping]

### Danh sách Mapping:
- Header: "Mapping đang có" + [Mở rộng tất cả] [Thu gọn tất cả]
- Mỗi mapping là một card collapsible:
  - **Header card (collapsed):** Tên | Badge chế độ ads | Chat ID nguồn | [▶ Run] [Sửa] [✕ Xóa]
  - **Body card (expanded):** Form sửa mapping đầy đủ
- Click vào header card: toggle expand/collapse
- Button [▶ Run]: tạo job forward, hiện progress bar realtime
- Button [✕ Xóa]: confirm → xóa mapping

---

## 8. Tab: Ads cuối (Alltask)

### Header: "Ads cuối phiên" + [Chạy ads cuối]

### Panel trái — Cấu hình:
- Toggle: "Bật ads cuối"
- Input: "Nguồn ads cuối" (link/chat/topic)
- Hiển thị parse hint bên dưới (chat ID, topic ID, msg ID)
- Radio group — "Cách lấy nguồn":
  - Lấy toàn bộ nguồn
  - Chỉ bài được nhập
- **Kênh ads đích:**
  - Header: [Chọn tất cả] [Bỏ chọn]
  - List checkbox: mỗi kênh trong registry có thể chọn
  - Scroll nếu nhiều
- Button [Lưu ads cuối]

### Panel phải — Trạng thái:
- Lần chạy cuối: thời gian, kết quả, số bài đã gửi
- Empty state nếu chưa chạy lần nào

---

## 9. Tab: Vận hành bot (Botops)

Tab này có 7 subtab, mỗi subtab là một section độc lập trong cùng page.

### Subtab: User của bot

**Header:** Tiêu đề + Filter bot (select) + Search input + [Xuất TXT]

**Stats row (4 card nhỏ):**
- Tổng user
- Premium users
- Số ngôn ngữ
- Bot đang lọc

**Table users:**
| Avatar | ID | Username | Tên | Premium | Ngôn ngữ | Lần cuối | Trạng thái | Actions |
|--------|-----|---------|-----|---------|---------|----------|-----------|---------|
- Button [Xem chi tiết] → mở detail panel slide-in từ phải
- Button [Chặn/Bỏ chặn] → toggle

**Detail panel** (slide-in hoặc modal):
- Thông tin đầy đủ user
- Lịch sử tương tác
- Nút đóng

---

### Subtab: Cấu hình bot

**Header:** "Cấu hình bot" + [Lưu cấu hình bot]

**Grid 2 cột — các module cards:**

Mỗi module card có:
- Header: Icon + Tên module + Toggle ON/OFF
- Body (chỉ hiện khi bật):
  - Checkbox "Trộn ads"
  - Input "Tự xoá sau N phút" (0 = không xoá)
  - Textarea "Caption thông báo" (hỗ trợ `{time}`)

**Danh sách module:**
1. **Xem lại bài cũ** (Archive) — icon archive
2. **File to link** — icon link — thêm options: protect content, allow forward, giới hạn xem
3. **Force join kênh** — icon users — thêm: input kênh bắt buộc, input tin nhắn từ chối
4. **Broadcast** — icon zap — thêm: tốc độ gửi, filter Premium only

---

### Subtab: Kho bài đã up (Archive)

**Header:** "Kho bài đã up" + [Tìm kiếm] + [Date picker] + [Làm mới]

**Table archive:**
| Thumbnail | Tên/Caption | Bot | Thời gian | Nhánh | Views | Actions |
|-----------|-------------|-----|----------|-------|-------|---------|
- Button [Xem]: mở modal preview
- Button [Xoá]: confirm → xóa

**Modal preview:** hiển thị nội dung bài, caption, link chia sẻ

---

### Subtab: File to link

**Bố cục 2 panel:**

**Panel trái — Tạo link mới:**
- Select: Chọn user Telegram
- Select: Chọn media
- Input number: Hết hạn sau N giờ (0 = không hết)
- Input number: Giới hạn xem (0 = không giới hạn)
- Toggle: Protect content
- Toggle: Cho phép forward
- Button [Tạo file link]

**Panel phải — Cấu hình backup forum:**
- Toggle: "Backup media về forum"
- Input: Forum ID / Link (sync 2 chiều với Admin bot → Mời bot)
- Hint: quyền cần thiết
- Buttons: [Lưu cấu hình backup] [Kiểm tra quyền bot] [Mở kho link share →]

---

### Subtab: Kho link share

**Header:** "Kho link share" + Filter trạng thái + [Làm mới] + [← Quay lại File to link]

**Table:**
| Token | Caption | Hết hạn | Views | Trạng thái | Actions |
|-------|---------|---------|-------|-----------|---------|
- Button [Xem link]: copy URL
- Button [Thu hồi]: vô hiệu hóa link
- Expired rows: dim/strikethrough

---

### Subtab: Mã xem (View codes)

**Bố cục 2 panel:**

**Panel trái — Cấu hình:**
- Card collapse toggle
- Input: Độ dài mã tối thiểu
- Input: Độ dài mã tối đa
- Toggle: Cho phép tạo mã mới
- Button [Lưu cấu hình]

**Panel phải — Danh sách mã:**
- Header + [Làm mới]
- Table: Mã | Label | Min views | Max views | Trạng thái | [Xóa]

---

### Subtab: Anti-flood

**Header:** "Anti-flood" + [Chạy mô phỏng] [Dừng]

**Panel trái — Tham số:**
- Input: Số user giả
- Input: Requests/giây
- Input: Burst
- Input: Thời gian chạy (giây)

**Panel phải — Kết quả:**
- 3 counter: Requests | OK | FloodWait
- Progress bar
- Terminal log (scrollable, monospace font)
  - Màu theo level: info/ok/warn/err

---

## 10. Tab: Admin bot (Botadmin)

### Subtab: Forum chung admin

**Bố cục 2 panel:**

**Panel trái — Cấu hình:**
- Input: Forum Chat ID
- Input number: Root topic ID
- Toggle: Tự tạo topic khi START
- Toggle: Auto pin link ngày mai
- Toggle: Mời bot vào forum chung
- Button [Lưu forum chung]

**Panel phải — Trạng thái:**
- Trạng thái kết nối forum
- Danh sách bot đã vào forum
- Quyền của từng bot

---

### Subtab: Topic quản lí từng bot

**Table:** Bot | Topic ID | Tên topic | Trạng thái | Metadata

---

### Subtab: Tiến độ up từng topic

**Header:** "Tiến độ up từng topic" + [Refresh tiến độ]

**Table:**
| Topic nguồn | Topic đích | Bài hiện tại | Bài kế tiếp | % | Cập nhật lúc |
|------------|-----------|-------------|------------|---|------------|
- Progress bar inline trong cell %

---

### Subtab: Mời bot vào forum

**Bố cục 2 panel:**

**Panel trái:**
- Input: Forum ID / Link
- Hint: quyền cần thiết
- Button [Lưu forum mời bot]

**Panel phải:**
- Table bot: Tên | Username | Quyền | Trạng thái | [Mời] [Kick]

---

### Subtab: Log hệ thống & spam

- Terminal-style log: cảnh báo spam, lỗi album, hết quyền, metadata update
- Filter theo level (INFO/WARN/ERROR)
- Auto-scroll khi có log mới

---

## 11. Tab: Kênh & folder (Channels)

### Header + toolbar:
- [+ Thêm kênh] [Load ảnh + tên kênh] [Sync folder] [Check kênh chết] [Xóa kênh chết]

### Panel: Danh sách kênh đích
- Search input: tìm theo id, tên, alias, @username
- Hiển thị count: "X kênh — Y ads · Z không ads"
- **Table:**
  | Avatar | Chat ID | Tên kênh | @Username | Alias | Loại | Liveness | Actions |
  |--------|---------|---------|----------|-------|------|---------|---------|
  - Liveness badge: alive/dead/no_access/unknown
  - Button [🔍 Check]: kiểm tra liveness
  - Button [✕]: xóa

### Panel: Kênh chết
- Các kênh đã được đánh dấu dead
- Table: Chat ID | Tên | Lần check | [Xóa khỏi pool] [Gỡ khỏi mapping]

### Modal: Thêm kênh
- Input: "Link / ID / username / addlist"
  - Hỗ trợ mọi định dạng: @username, https://t.me/..., -100xxx, link addlist folder
- Hint text hướng dẫn định dạng
- Button [Hủy] [OK]

---

## 12. Tab: Lịch auto (Schedule)

### Bố cục 2 panel:

### Panel trái — Cấu hình chung:
- Toggle: "Bật lịch auto"
- Input time: Giờ chạy
- Select: Timezone (Asia/Bangkok, Asia/Ho_Chi_Minh, UTC)
- Select: Chu kỳ lặp
  - Một lần trong ngày
  - Mỗi 6 giờ
  - Mỗi 3 giờ
  - Mỗi giờ
- Toggle: "Chỉ chạy khi đã START"
- Toggle: "Dừng nếu thiếu media bắt buộc"
- Button [Lưu lịch]

### Panel phải — Phân luồng chạy:
- Subtitle: "Kéo thả để đổi thứ tự bước trong một lượt"
- **Drag-and-drop list** — mỗi item:
  - Icon grip (handle kéo thả)
  - Label bước: "1. Up bài ads (Mapping chính)"
  - Meta: "mapping × 4"
  - Toggle bật/tắt bước này
- Thứ tự mặc định:
  1. Up bài ads (Mapping chính)
  2. Ads cuối phiên
  3. Archive bot
  4. Backup dữ liệu

---

## 13. Tab: Admin userbot (Telegram)

### Bố cục 2 panel hàng trên:

### Panel trái — Đăng nhập userbot:

**Status block:**
- Badge trạng thái: "Đã kết nối" (green) / "Chưa đăng nhập" (muted) / "Pending OTP" (amber)

**Khi đã đăng nhập — Logged-in card:**
- Avatar icon
- Tên Telegram + @username
- Số điện thoại (masked: +66•••••)
- Thời gian đăng nhập
- Buttons: [Đổi tài khoản] [Đăng xuất]

**Khi chưa đăng nhập — Login flow (multi-step):**

*Bước 1 — Phone:*
- Input: Số điện thoại (format +66xxxxxxxxx)

*Bước 2 — OTP (hiện sau khi gửi code):*
- Input: Mã OTP 5 chữ số (inputmode=numeric, autocomplete=one-time-code)
- Hint: "Mã có hiệu lực ~5 phút"

*Bước 3 — 2FA (chỉ hiện nếu tài khoản bật 2FA):*
- Input: Mật khẩu Cloud Password (type=password)

**Toolbar login:**
- [Gửi mã OTP] → disabled sau khi gửi
- [Xác nhận login] → enabled sau khi có OTP
- [Đăng xuất]

**Toggles:**
- "Tự kết nối lại khi mở tool"
- "Chỉ cho admin userbot đã login thao tác dữ liệu"

---

### Panel phải — Cấu hình API Hash:

- Input: API ID (số)
- Input: API Hash (32 ký tự, type=password)
- Input readonly: Đường dẫn session
- Input: Device model
- Input: App version
- Info box: "Token bot tách riêng — nằm ở các tab khác"
- Button [Lưu cấu hình API]

---

### Panel dưới — Bot credentials:

**Header:** "Bot credentials" + [+ Thêm bot]

**Table:**
| Tên bot | @Username | Token fingerprint | Validated | Trạng thái | Actions |
|---------|----------|-----------------|----------|-----------|---------|
- Fingerprint: chỉ hiện `...XXXX` (4 ký tự cuối)
- Button [Xác thực lại]: gọi getMe
- Button [Xóa]: confirm → xóa

**Modal: Thêm bot**
- Input: Tên bot
- Input: Bot Token (type=password, autocomplete=new-password)
- Hint: "Token mã hoá AES-256, chỉ hiện fingerprint sau khi lưu"
- Button [Hủy] [Xác thực & Lưu]

---

## 14. Tab: Backup & dữ liệu (Import)

### Header: "Backup & dữ liệu" + [Backup ngay]

### Panel: Import dữ liệu cũ
- **Dropzone** (kéo thả file):
  - "Kéo file / ZIP vào đây"
  - Hint: định dạng hỗ trợ (.env, channels.json, topic_map.txt, *.session, auto_config.json)
  - Hover: highlight border
- Buttons: [Preview import] [Import từ workspace] [Resync disk]

### Panel: Lịch sử backup
- Header + [Làm mới]
- Table: Filename | Size | SHA256 prefix | Thời gian | Status | [⬇ Download]

### Panel: Lịch backup tự động
- Toggle: "Backup sau khi chạy lịch up bài"
- Input: "Giữ backup trong N ngày"
- Input readonly: "Thư mục backup: data/backups/"
- Button [Lưu lịch backup]

### Panel: Audit log & Sandbox
- Header + [Bắt đầu ghi] [Replay] [Export JSON] [Xoá log]
- 3 inputs: Tốc độ replay (ms) | Số tin đã ghi | Trạng thái
- Table audit: thời gian | actor | action | resource | success

---

## 15. Tab: Log realtime (Logs)

### Header: "Log realtime" + Status badge SSE + [Clear logs]

**SSE Status badge:**
- "Live" (green dot, đang nhận SSE)
- "Connecting..." (amber, đang kết nối)
- "Polling" (amber, dùng REST fallback)

**Terminal component:**
- Style: terminal/console (background rất tối, font monospace)
- Decorative bar trên: 3 chấm tròn (đỏ/vàng/xanh như macOS)
- Log area (scroll):
  - Mỗi dòng: `[HH:MM:SS] [LEVEL] message`
  - Màu theo level: INFO (trắng) / OK (xanh lá) / WARN (vàng) / ERROR (đỏ)
  - Auto-scroll xuống cuối khi có log mới
  - Giữ tối đa ~500 dòng (cũ hơn tự xóa)

---

## 16. Toast Notifications

**Vị trí:** Bottom-right, stack từ dưới lên  
**Animation:** slide up fade in  
**Types:**
- SUCCESS (ok): border màu xanh lá
- ERROR (err): border màu đỏ, duration dài hơn (6s)
- WARNING: border màu vàng
- INFO: border muted

**Mỗi toast có:**
- Text message (textContent — không innerHTML để tránh XSS)
- Nút [×] đóng
- Tự đóng sau N giây

---

## 17. Modals

**Overlay:** backdrop mờ tối, click ra ngoài để đóng  
**Escape key:** đóng modal  
**Animation:** fade + scale hoặc slide up  

**Modals hiện có:**
1. **Thêm kênh** — 1 input, hints, [Hủy][OK]
2. **Thêm bot** — 2 inputs (tên + token), [Hủy][Xác thực & Lưu]
3. **Confirm destructive action** — text confirm, [Hủy][Xóa/Xác nhận] (danger style)
4. **Preview bài archive** — hiển thị nội dung, caption, link

---

## 18. Components tái sử dụng

### Toggle Switch
- Kiểu: pill toggle (on/off)
- On: màu accent/blue
- Off: màu muted/gray

### Progress Bar
- Inline bar
- Fill màu blue, animate smooth

### Badge/Tag
- Pill shape, nhỏ
- Màu theo loại: blue/green/red/amber/muted/purple

### Card collapsible
- Header clickable
- Có chevron icon xoay khi expand/collapse
- Body ẩn/hiện với animation

### Drag-and-drop list
- Handle icon ở đầu mỗi item
- Visual feedback khi kéo

### Stat Card
- Label nhỏ trên
- Số lớn giữa
- Subtitle nhỏ dưới
- Icon góc phải

### Run note / Info box
- Background màu nhạt theo type
- Strong label + nội dung
- Types: info (blue), warning (amber), success (green)

---

## 19. Hành vi tương tác quan trọng

### Navigation:
- Tab switch: instant, không reload trang
- Subtab switch: chuyển panel trong cùng section
- Active state persist qua localStorage (preference)

### Forms:
- Validation client-side trước khi gửi
- Button disabled + loading state khi đang gửi
- Reset form sau khi submit thành công
- Lỗi hiển thị inline, không alert()

### Destructive actions:
- Luôn có confirm modal trước khi xóa
- Label nút confirm dùng chữ mô tả hành động (không chỉ "OK")

### Mapping card:
- Click header → expand/collapse body
- [Mở rộng tất cả] / [Thu gọn tất cả] → toggle tất cả cùng lúc

### Login flow userbot:
- Bước 1 (phone) → Gửi OTP → Bước 2 (OTP) hiện ra
- Confirm OTP → nếu 2FA bật → Bước 3 hiện ra
- Thành công → ẩn form, hiện logged-in card
- Đăng xuất → reset về bước 1

### Job progress (SSE):
- Khi tạo job → progress bar xuất hiện trong mapping card
- Nhận event SSE → cập nhật phần trăm realtime
- Khi xong → toast thông báo kết quả

### Channel liveness:
- `alive` → badge xanh
- `dead` → badge đỏ
- `no_access` → badge vàng (không tự xóa)
- `unknown` → badge muted

### Keyboard shortcuts:
- `Ctrl+K` → mở command palette (tìm nhanh tab/action)
- `Escape` → đóng modal/palette

---

## 20. Responsive

### Desktop (≥1280px):
- Layout đầy đủ: sidebar + main
- Grid 12 cột

### Tablet (768–1279px):
- Sidebar thu nhỏ hoặc icon-only
- Grid 6 cột

### Mobile (<768px):
- Sidebar ẩn, hamburger menu → drawer overlay
- Grid 1 cột (tất cả span full width)
- Topbar: chỉ hiện logo + status + hamburger

---

## 21. Data states cho mọi component

Mọi list/table phải có đủ 4 state:

| State | Hiển thị |
|-------|---------|
| **Loading** | Spinner hoặc skeleton |
| **Empty** | Icon + tiêu đề + subtitle hướng dẫn |
| **Data** | Content bình thường |
| **Error** | Icon cảnh báo + message lỗi + nút retry |

---

## 22. Thứ tự ưu tiên khi redesign

1. Đảm bảo đủ tất cả 10 tab + subtab
2. Đảm bảo đủ mọi form field và button
3. Đảm bảo đủ 4 data state cho list
4. Navigation hoạt động (tab switch + subtab switch)
5. Toggles, checkboxes, selects hoạt động visual
6. Toast notification
7. Modal confirm cho destructive action
8. Sau cùng mới đến style/theme

---

*File này đủ để AI thiết kế lại toàn bộ UpBain Control với bất kỳ stack nào (React, Vue, Svelte, plain HTML) và bất kỳ design system nào (Material, Tailwind, Shadcn, Ant Design, v.v.)*
