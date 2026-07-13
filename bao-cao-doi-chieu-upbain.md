# Báo cáo đối chiếu UpBain

Ngày kiểm tra: 2026-07-13  
Phạm vi đọc:

- `C:\Users\Admin\Documents\PHANTICH\tong-hop-phuong-phap-code.md`
- `C:\Users\Admin\Videos\HHH\index.html`
- `C:\Users\Admin\Videos\HHH\v30autoxep_co_all CHECK.py`
- Các nguồn Telegram, GitHub và cộng đồng developer công khai ghi ở cuối báo cáo.

## 1. Kết luận ngắn

`index.html` hiện là prototype dashboard lớn, chưa phải ứng dụng vận hành hoàn chỉnh. Thư mục `HHH` chỉ có `index.html`, `lucide.min.js` và một tool Pyrogram; không có backend web tương ứng. Giao diện đang trộn bốn loại hành vi: API giả định, state trong RAM, fallback `localStorage`, và simulator/demo.

JavaScript nội tuyến qua kiểm tra cú pháp, nhưng runtime và hợp đồng dữ liệu có lỗi chặn chức năng. Việc trang hiển thị được không chứng minh các nghiệp vụ Telegram hoạt động.

Baseline đã đo:

| Lớp kiểm tra | Kết quả |
|---|---:|
| Dung lượng `index.html` | 526.944 byte |
| Nút tĩnh trong HTML | 86 |
| Form tĩnh | 4 |
| Input/select/textarea tĩnh | 95 |
| Nút trong DOM sau bootstrap | 94 |
| Lời gọi `fetch('/api/...')` tương đối | 42 |
| Inline script | 1, cú pháp hợp lệ |
| Backend trong thư mục `HHH` | Không có |

Con số control không dừng ở 86/95 vì nhiều nút và input được sinh từ template JavaScript. Một audit hoàn chỉnh phải tách ba lớp: HTML tĩnh, template động và DOM thật sau khi bootstrap.

Phân loại hiện trạng nút:

| Nhóm | OK ở tầng UI hiện tại | Broken/partial/dead/conflict/security/simulation |
|---|---:|---:|
| 86 nút tĩnh | 48 | 38 |
| 63 nút động đã tìm thấy | 21 | 42 |

`OK` ở đây chỉ có nghĩa handler/UI cục bộ làm đúng phần được mô tả, không tự động có nghĩa backend hoặc Telegram side effect đã được chứng minh.

## 2. Bằng chứng runtime

Trang được phục vụ read-only trên localhost và mở bằng trình duyệt thật. `/api/auth/status` trả 404, nhưng dashboard vẫn tự boot. Console đồng thời báo fallback cho bot config, forum config, userbot config, logs và view-code config.

Trong trạng thái backend không có, giao diện vẫn hiện:

- `Realtime local`
- `Userbot: Ready`
- `Auto: Armed`

Đây là false-success: trạng thái trình bày không phản ánh backend hay kết nối Telegram thật.

## 3. Lỗi ưu tiên cao

| Mức | Phát hiện | Bằng chứng chính | Hậu quả |
|---|---|---|---|
| P0 | Admin auth fail-open | `index.html:8981-8989` | `/api/auth/status` lỗi vẫn cho vào toàn bộ dashboard. |
| P0 | Token bot được lưu trong browser | `8201-8239`, `10552-10558`, `12387` | Mapping chứa token thô bị ghi `localStorage` và hydrate lại vào DOM. |
| P0 | API hash được trả và điền lại vào DOM | `11651-11661` | Secret xuất hiện trong response/browser thay vì chỉ ở secret store phía server. |
| P0 | DOM XSS ở trạng thái login | `11392-11399`, `11455-11480` | Phone/error không được escape trước khi đưa vào `innerHTML`. |
| P0 | Runtime đọc sai response envelope | `_get/_post`: `5348-5377`; consumer: `11191-11200`, `12317-12320` | Scan/ads luôn cho rằng runtime dừng; START xong STOP vẫn bị vô hiệu hóa. |
| P1 | File-to-link tham chiếu hàm không tồn tại | `adsChannels()` tại `9909`; `selectLinkToken()` tại `11929`, `11945` | `adsChannels` đang nằm sau một hint DOM cũng bị thiếu; khi có saved-link row, click chọn row sẽ gọi `selectLinkToken` và có thể nổ `ReferenceError`. |
| P0 | Badge backend không có trong DOM | HTML chỉ có `liveLabel` tại `3886`; JS tìm ID khác tại `12333-12336`, `12628-12659` | Nhãn `Realtime local` không bao giờ phản ánh health thật. |
| P0 | File-to-link có rủi ro lệch Telegram Terms | Bot Developer Terms, mục 5.2(e) | Không được biến Bot Platform thành website cloud storage/CDN. |
| P1 | Hai chiến lược API origin | `API_BASE` cố định tại `5409`; auth/SSE/nhiều API dùng same-origin | Chạy ở `localhost`, port khác, LAN hoặc deploy sẽ 404/CORS/mixed state. |
| P1 | Handler generic và handler thật cùng gắn | `11155-11190`; các action thiếu trong skip-set | Một click vừa báo “chưa hỗ trợ” vừa chạy save/relogin. |
| P1 | Lưu mapping báo thành công quá sớm | `12371-12411` | Bỏ qua `topicDestinations`; backend lỗi vẫn cho cảm giác đã lưu. |
| P1 | Xóa local dù backend xóa lỗi | `8225-8236` | Browser và database lệch nhau. |
| P1 | Nút động không được bind | Quét `[data-action]` một lần tại `11182`; nút sinh sau đó | Run/Scan/Check/Xóa động có thể chết. |

Ba action tĩnh bị gắn cả generic “chưa hỗ trợ” lẫn handler riêng là:

- `relogin_userbot`
- `save_admin_bot_invite_forum`
- `save_filelink_backup`

## 4. Đối chiếu từng khu vực giao diện

| Khu vực | Control chính đã kiểm tra | Trạng thái thật hiện tại |
|---|---|---|
| Điều hướng | 10 tab, 12 subpage, command palette | Điều hướng/hash hoạt động; chưa chứng minh nghiệp vụ. |
| Topbar | Thử lại, START, STOP | Thử lại chỉ reload; START/STOP lỗi response envelope. |
| Dashboard | Refresh máy, Scan | Stats lấy object local; Scan bị runtime check chặn. |
| Topic/mapping | Thêm, hủy, expand/collapse, thêm/xóa đích/token, lưu, chạy từng mapping | Một phần hoạt động local; lưu bỏ qua destination stack; run từng mapping chỉ toast/log. |
| Nguồn ads | Lưu, Check, Xóa, sinh `topic_map.txt` | Download map hoạt động; response probe đọc sai tầng; nút động Check/Xóa thiếu handler. |
| Ads cuối | Chạy, chọn tất cả, bỏ chọn, lưu | Cấu hình lưu local/app-data; chạy thật bị runtime envelope chặn. |
| User của bot | Search/filter, export, block | Export bị bind hai lần; filter bot thiếu listener; block chỉ đổi RAM. |
| Cấu hình bot | Lưu modules | Có API giả định; fallback `localStorage` không được load lại nhất quán. |
| Archive | Refresh, filter, action động | Refresh chỉ xóa filter; archive không được load từ backend. |
| File-to-link | Tạo link, lưu backup, refresh, mở kho | Gọi hàm thiếu, dữ liệu đầu vào rỗng, URL/token demo; save có false-success. |
| View codes | Lưu, refresh, xóa | Một số handler bị bind hai lần; cần contract và persistence thật. |
| Anti-flood | Start/Stop | Chỉ là simulator local, không phải Telegram runtime. |
| Admin bot | Lưu forum, tiến độ, mời bot, log | Progress đọc sai envelope/field; save invite vừa báo unsupported vừa false-success. |
| Kênh/folder | Thêm, load metadata, sync, check/xóa dead | Metadata gọi nhầm API object; sync chỉ đếm; parser/persistence còn lệch backend. |
| Lịch auto | Các control lịch/flow | Gần như chỉ UI; không có save/change/drag-drop/job bền vững. |
| Admin userbot | Save config, gửi OTP, confirm, logout, relogin | Có luồng API giả định nhưng secret/XSS/selector/bind lỗi; nút thứ hai cùng action không được bind. |
| Backup/import | Backup, preview, import workspace, resync, lịch | Backup có API giả định; preview/import chỉ toast; dropzone và lịch không có handler. |
| Audit/sandbox | Xóa audit, thêm bot, record/replay/export/clear | Xóa nhầm loại log; wizard tạo bot demo; sandbox không thực sự record. |
| Logs | Clear | Xóa UI rồi có thể báo backend thành công dù wrapper trả lỗi envelope. |

Ma trận 86 nút tĩnh được bàn giao riêng trong `ma-tran-nut-index.csv`.

## 5. Tài liệu phương pháp: phần đúng và phần phải sửa

Tài liệu 820 dòng là catalog kỹ thuật, không phải PRD hay đặc tả UI. Nó mô tả bốn nhóm tool: caption entities, batch forward, web/bot/Telethon và auto-xếp bài Pyrogram. Chỉ hai nút được nêu trực tiếp là “Tham gia kênh” và “Kiểm tra lại”; phần còn lại của UI là suy diễn.

Các phương pháp đáng giữ:

- Bảo toàn message entities và custom emoji.
- Batch forward, split retry, FloodWait retry đúng batch.
- Kiến trúc phân tầng, progress callback, SSE, resume/checkpoint.
- Album debounce, file/link metadata, WAL/UPSERT/soft delete.
- Force-join, backup rotation, login OTP/2FA có state.
- Bounded concurrency, round-robin bền vững, chatlist sync và error classification.

Các điểm phải sửa trước khi biến thành code:

| Vấn đề trong tài liệu | Sửa đúng |
|---|---|
| Schema `media_albums` không có `is_active` nhưng soft-delete dùng cột này | Thêm migration/cột/index và test restore, hoặc thiết kế trạng thái khác. |
| Gọi `2 * (attempt + 1)` là exponential backoff | Dùng exponential có cap + jitter, hoặc gọi đúng là linear. |
| Truyền nguyên entities sau khi đổi text | Chỉ passthrough nếu text không đổi; khi chèn/cắt phải transform offset/length theo UTF-16 và validate range. |
| Global flood gate giữ lock trong lúc sleep | Cập nhật shared deadline trong lock, release lock rồi sleep; persist `not_before` nếu job bền vững. |
| Token số ngẫu nhiên được gọi là “duy nhất” | Dùng CSPRNG đủ entropy + UNIQUE constraint + collision retry. |
| WAL + `check_same_thread=False` được coi là đủ an toàn | Connection/transaction ownership rõ, busy timeout, lock/queue hoặc ORM session đúng scope. |
| Dual-write file + DB | Chọn một source of truth hoặc transaction/outbox/reconciliation. |
| Fail-open force-join | Nội dung nhạy cảm phải fail-closed; lỗi phải audit/alert. |
| `ChannelPrivate` bị coi là dead | Phân loại `unknown/no_access`, không tự xóa. |
| Checkpoint “mất tối đa một batch” | Định nghĩa delivery/checkpoint order; test duplicate và mất dữ liệu sau crash. |

## 6. Ranh giới API cần hiểu đúng

| Lớp | Nên làm gì |
|---|---|
| MTProto/user client | Đọc lịch sử, clone forum/topic, edit caption giữ entities, import/sync folder, scan nguồn, login phone/OTP/2FA. |
| Bot API | `/start`, bot archive, broadcast, membership, copy/forward các message đã biết ID, forum action khi bot đủ quyền. |
| Web admin | Điều khiển, cấu hình, audit, job status; tuyệt đối không chứa secret trong browser. |
| Mini App | Chỉ cân nhắc cho trải nghiệm user trong Telegram; `initData` phải verify HMAC ở backend. |

Bot API không có API đọc tùy ý toàn bộ lịch sử chat. Những tính năng clone/scan lịch sử phải đi qua MTProto và chịu Telegram API Terms.

`file_id` riêng cho từng bot, không thể chuyển token/bot rồi tái sử dụng tùy ý. Nếu lưu media nhiều bot phải lưu `origin_bot_id`; với link public bền vững nên dùng object storage do mình sở hữu và presigned URL, không dùng Telegram làm CDN.

## 7. Nguồn đã research và quyết định

### Nguồn chính thức Telegram

| Nguồn | Dùng để quyết định |
|---|---|
| [Telegram Bot API](https://core.telegram.org/bots/api) | `copyMessages`/`forwardMessages` 1-100 ID tăng dần, album, forum, `getChatMember`, `getFile`, file ID. |
| [Bots FAQ](https://core.telegram.org/bots/faq) | Rate limits/broadcast và 429; không có một `GLOBAL_RATE` đúng cho mọi chat/method. |
| [Bot Platform Developer Terms](https://telegram.org/tos/bot-developers) | Privacy, retention, anti-spam, chống né rate limit và rủi ro “cloud storage sites”. |
| [Telegram API](https://core.telegram.org/api) | Phân biệt Bot API, Telegram API/MTProto và TDLib. |
| [User authorization](https://core.telegram.org/api/auth) | Phone → code/hash → sign-in → SRP 2FA. |
| [Forum topics](https://core.telegram.org/api/forum) | Topic ID, reply/top-message và quyền forum. |
| [Message entities](https://core.telegram.org/api/entities) | Offset/length UTF-16 và custom emoji. |
| [Creating a Telegram Application](https://core.telegram.org/api/obtaining_api_id) | `api_id`/`api_hash` riêng, không dùng credential mẫu. |
| [Telegram API Terms](https://core.telegram.org/api/terms) | Consent, privacy, anti-abuse và hạn chế automation. |
| [Mini App validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app) | Không tin `initDataUnsafe`; verify backend. |

### Mã nguồn/upstream

| Project | Tình trạng đã xác minh 2026-07-13 | License/ghi chú | Quyết định |
|---|---|---|---|
| [Telethon tại Codeberg](https://codeberg.org/Lonami/Telethon) | Source chính đã chuyển từ GitHub; v1 maintenance nhưng vẫn cập nhật layer/bugfix | MIT | Ứng viên MTProto chính, cần ADR và pin version. |
| [Telethon GitHub cũ](https://github.com/LonamiWebs/Telethon) | Archived mirror, README trỏ sang Codeberg | MIT | Không dùng GitHub cũ làm tín hiệu “project đã chết”. |
| [Pyrogram](https://github.com/pyrogram/pyrogram) | Archived; README ghi không còn maintained/support | LGPL-3.0 | Không chọn cho code mới; chỉ dùng để hiểu/migrate `v30`. |
| [Hydrogram](https://github.com/hydrogram/hydrogram) | Fork active, cộng đồng nhỏ | LGPL-3.0 | Cân nhắc trong decision matrix, không mặc định chọn. |
| [Pyrofork](https://github.com/Mayuri-Chan/pyrofork) | Fork Pyrogram active | LGPL-3.0 | Có thể là cầu nối migration ngắn hạn. |
| [aiogram](https://github.com/aiogram/aiogram) | Active, async, theo Bot API mới | MIT | Ứng viên Bot API greenfield. |
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | Active | Repo có dual notice GPL-3.0/LGPL-3.0 | Dùng nếu phù hợp code hiện hữu; không trộn hai bot framework. |
| [TDLib](https://github.com/tdlib/td) | Official/active | BSL-1.0 | Chỉ chọn nếu chấp nhận độ phức tạp client native. |
| [Local Bot API server](https://github.com/tdlib/telegram-bot-api) | Official/active | BSL-1.0 | Chỉ khi thực sự cần file lớn và vận hành được hạ tầng. |
| [telegram_media_downloader](https://github.com/Dineshkarthik/telegram_media_downloader) | Có resume/web UI và đã migrate Pyrogram → Telethon | MIT | Nguồn học state/download; phải review code trước khi áp dụng. |
| [Telegram-Archive](https://github.com/GeiserX/Telegram-Archive) | Incremental archive/viewer/RBAC | GPL-3.0 | Học kiến trúc, không sao chép nếu không chấp nhận copyleft. |

Nguồn loại bỏ: các repo quảng cáo bypass protected content, dùng nhiều token để né rate limit hoặc biến Telegram thành “unlimited cloud storage”, dù license cho phép sao chép.

### Kênh/community Telegram

- [@BotNews](https://t.me/BotNews): tin Bot API chính thức.
- [@BotTalk](https://t.me/BotTalk): thảo luận bot developer.
- [@BotSupport](https://t.me/BotSupport): hỗ trợ bot/Mini App.
- [@TelethonUpdates](https://t.me/TelethonUpdates) và [@TelethonChat](https://t.me/TelethonChat).
- [@aiogram](https://t.me/aiogram).
- [python-telegram-bot group](https://t.me/pythontelegrambotgroup).
- [@HydrogramChat](https://t.me/HydrogramChat).
- [@pyrogram](https://t.me/pyrogram): chính channel này ghi project không còn được duy trì.

Community là lead để tìm vấn đề, không phải spec. Mọi claim kỹ thuật phải được đối chiếu với official docs hoặc upstream code. Không gửi token, session, OTP, 2FA hay API hash cho group/admin.

## 8. Hướng kiến trúc nên buộc AI đánh giá

Không chốt thư viện chỉ vì tài liệu cũ dùng nó. AI phải viết ADR và chấm ít nhất hai phương án. Baseline hợp lý để đánh giá:

- Backend Python async có OpenAPI và schema validation.
- Một adapter MTProto, một adapter Bot API; fake adapter cho test.
- Database là source of truth; migration versioned.
- Job bền vững có queue/state/items/events, idempotency, cancel/resume và persisted FloodWait deadline.
- SSE có event ID, heartbeat, reconnect và REST fallback.
- Một API origin và một response envelope thống nhất.
- `localStorage` chỉ dành cho theme/tab/filter, không chứa nghiệp vụ hoặc secret.
- Public file share dùng S3/MinIO/R2 hoặc storage tương đương; Telegram chỉ giao nội dung trong Telegram.

## 9. Tiêu chuẩn “hoàn thành” thực sự

Chỉ coi web hoàn chỉnh khi:

- Mọi control tĩnh và động có owner, API, persistence, permission, state lỗi/loading và browser test.
- Không còn dead button, duplicate handler, mock giả live hay toast false-success.
- Frontend/OpenAPI/response schema khớp nhau.
- Backend, DB, migrations, worker, scheduler và SSE chạy sau restart.
- Secret không xuất hiện trong HTML, browser storage, API GET, log, SSE, URL hoặc screenshot.
- Test unit/integration/browser pass và browser console/network sạch.
- Live Telegram test chỉ chạy trong account/chat sandbox allowlist; không mass-send hoặc đụng production.
- Thiếu credential/OTP thì ghi đúng blocker, không đổi sang mock rồi báo hoàn thành.
