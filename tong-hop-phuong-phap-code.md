# Tổng hợp phương pháp code (trích từ các tool)

> File tổng hợp các đoạn code hay theo dạng: **đoạn code + chức năng**.

---

## Tool 1 — Telegram Caption Editor (`tg_caption_editorv8.py`)

### Chủ đề: Giữ nguyên định dạng gốc khi sửa caption

Kỹ thuật chính: **bảo toàn "message entities"** — Telegram lưu định dạng (in đậm, nghiêng, link, premium emoji) tách rời khỏi text dưới dạng danh sách "chú thích theo vị trí" (offset + length). Giữ định dạng = truyền lại nguyên entities gốc, KHÔNG parse qua Markdown/HTML.

#### 1. Đọc caption giữ cả định dạng

```python
return msg.message, msg.entities
```

**Chức năng:** Lấy CẢ text (`msg.message`) LẪN định dạng (`msg.entities`), không chỉ lấy chữ.

#### 2. Ghi caption giữ định dạng (cốt lõi nhất)

```python
await client.edit_message(entity, msg_id,
                          text=new_text,
                          formatting_entities=new_entities)
```

**Chức năng:** Truyền lại entities gốc qua `formatting_entities` → giữ nguyên định dạng + premium emoji 100%.

#### 3. Nhận biết premium emoji

```python
has_emoji = any(getattr(e, "custom_emoji_id", None) for e in (msg.entities or []))
```

**Chức năng:** Duyệt entities, tìm cái có `custom_emoji_id` → phát hiện premium emoji.

#### Thuật ngữ liên quan

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **Message Entities** | Danh sách "chú thích định dạng" theo vị trí (offset + length), tách rời khỏi text |
| **`formatting_entities`** | Tham số Telethon để truyền entities gốc vào khi edit → giữ định dạng |
| **Entity preservation / passthrough** | Kỹ thuật giữ định dạng bằng cách truyền lại entities gốc, không parse qua Markdown/HTML |
| **`MessageEntityCustomEmoji`** | Loại entity riêng cho premium emoji, mang `custom_emoji_id` |
| **Offset-based formatting** | Mô hình định dạng của Telegram: dựa trên vị trí chữ, không nhúng thẻ như HTML |
| **Library (thư viện)** | Code viết sẵn của người khác, cài về để dùng (vd: `telethon`) |
| **Third-party library** | Thư viện bên thứ ba, cài bằng `pip install` (vd: `telethon`, `cryptg`) |

---

## Tool 2 — Telegram Forwarder BATCH MODE (`forward_asmtoki_batch.py`)

### Chủ đề: Forward hàng loạt (Batch Forwarding)

Kỹ thuật chính: **Batch = gom nhiều tin, gửi 1 lần**. Thay vì forward từng tin (100 tin = 100 request → chậm + dễ bị Telegram chặn), tool gom nhiều tin rồi gửi 1 request cho cả cụm (100 tin = 2 request).

#### 1. Gửi hàng loạt bằng `ForwardMessagesRequest`

```python
await client(ForwardMessagesRequest(
    from_peer=src_peer,
    id=list(msg_ids),          # ← danh sách NHIỀU id, không phải 1
    to_peer=dst_peer,
    top_msg_id=topic_id,       # ← forward đúng vào topic
))
```

**Chức năng:** Forward cả một danh sách `id=[...]` trong 1 request duy nhất (Telegram cho tối đa 100 id/request).

#### 2. Batch buffer — gom tin theo topic

```python
async def push(msg_id: int, topic_id):
    t_key = topic_id
    batch_buf[t_key].append(msg_id)
    if len(batch_buf[t_key]) >= BATCH_SIZE:   # đủ 50 → gửi
        await flush_bucket(t_key, force=True)
```

**Chức năng:** Nhét id vào "giỏ" theo từng topic. Khi giỏ đủ `BATCH_SIZE` (50) thì mới gửi → tin của topic khác nhau không bị lẫn.

#### 3. Token Bucket — giới hạn tốc độ (rate limit)

```python
class TokenBucket:
    async def acquire(self, n=1.0):
        # mỗi request tiêu 1 "token", token tự hồi theo thời gian
        # hết token → phải chờ
```

**Chức năng:** Khống chế số request/giây (`GLOBAL_RATE = 10`) → tránh spam quá nhanh làm Telegram khóa (FloodWait).

#### 4. Split đôi khi lỗi — cô lập id "xấu"

```python
if len(msg_ids) > 1:
    mid = len(msg_ids) // 2
    lok, lf = await _try_batch(..., msg_ids[:mid], ...)   # nửa trái
    rok, rf = await _try_batch(..., msg_ids[mid:], ...)   # nửa phải
    return lok + rok, lf + rf
```

**Chức năng:** Nếu 1 batch lỗi, chia đôi rồi thử lại từng nửa → tìm ra đúng id gây lỗi, phần còn lại vẫn forward được (không mất cả lô).

#### 5. FloodWait — chờ rồi tiếp, không mất tin

```python
except FloodWaitError as e:
    await asyncio.sleep(e.seconds + 2)   # Telegram bắt chờ → ngủ đúng số giây
    continue                             # rồi thử lại chính batch đó
```

**Chức năng:** Khi bị Telegram bắt chờ, tool ngủ đủ số giây rồi thử lại đúng batch đó → không bỏ sót tin.

#### Thuật ngữ liên quan

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **Batch forwarding** | Gom nhiều tin, forward 1 request thay vì từng tin |
| **`ForwardMessagesRequest`** | Lệnh Telethon nhận danh sách `id=[...]` để forward hàng loạt |
| **Batch buffer** | "Giỏ" tạm chứa id, đủ số lượng mới gửi |
| **Token Bucket** | Thuật toán giới hạn tốc độ request/giây |
| **FloodWait** | Telegram bắt chờ khi gửi quá nhanh |
| **Split retry** | Chia đôi batch lỗi để cô lập id gây lỗi |

---

## Tool 3 — Forum Converter Bot (dự án web: Flask + Bot + Telethon)

Dự án web hoàn chỉnh gồm 3 thành phần: **Telethon Forwarder** (clone forum), **Telegram Bot** (tạo link, forward), **Web Admin Dashboard** (quản trị). Dưới đây là toàn bộ phương pháp theo nhóm.

### 3.0. Cách sắp xếp code — kiến trúc phân tầng

```
├── config/      → chỉ đọc cấu hình (.env)
├── database/    → chỉ làm việc với SQLite
├── forwarder/   → lõi Telethon: forward, state, chạy nền
├── bot/         → Telegram bot (lệnh, handler, check join)
├── utils/       → tiện ích dùng chung (backup, token, thumbnail)
├── web/         → giao diện (templates + css/js)
├── deploy/      → script cài đặt VPS/Windows
├── app.py       → Flask web server + REST API
└── run.py       → launcher tổng, khởi động tất cả
```

**Nguyên tắc:** file tầng trên (`app.py`) import file tầng dưới (`forwarder`, `database`), không bao giờ ngược lại.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **Separation of concerns** | Mỗi module lo đúng 1 việc |
| **Layered architecture** | Tầng trên gọi tầng dưới, không ngược lại |

---

### 3.1. Khởi động & giám sát (run.py)

#### Unified launcher — Bot chạy chính, Web chạy nền
```python
_start_web_thread()          # Web chạy trong thread nền
if "--no-watchdog" not in args:
    _start_web_watchdog()    # Thread giám sát
run_bot()                    # Bot chạy ở main thread (giữ chương trình sống)
```
**Chức năng:** Chạy đồng thời Bot + Web trong 1 lệnh bằng **threading** (đa luồng).

#### Web Watchdog — tự hồi sinh khi web chết
```python
while not _watchdog_stop.wait(WATCHDOG_INTERVAL):   # mỗi 60s
    if not _web_is_healthy() or not thread_alive:
        _start_web_thread()   # web chết → tự bật lại
```
**Chức năng:** Cứ 60s ping `/health`, web sập thì tự khởi động lại (bot không bị ảnh hưởng). Gọi là **health-check + auto-restart**.

---

### 3.2. Chạy phiên forward nền (runner.py)

#### Mỗi phiên 1 thread + event loop riêng
```python
def run_in_thread():
    loop = asyncio.new_event_loop()   # mỗi phiên 1 event loop riêng
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_async_run(...))
t = threading.Thread(target=run_in_thread, daemon=True)
t.start()
```
**Chức năng:** Nhiều phiên forward chạy song song, không chặn web. Kết hợp **thread + asyncio**.

#### Progress callback — lõi báo tiến độ ngược lên web
```python
def progress_cb(p: dict):
    session_info["progress"] = p
    db_set_session_progress(db_key, p)   # lưu DB
    session_info["log"].append(...)      # web đọc để hiện SSE
```
**Chức năng:** Hàm forward gọi ngược `progress_cb` mỗi khi có tiến triển → web nhận được. Gọi là **callback pattern**.

#### Lazy client creation — tạo client đúng thread
```python
# KHÔNG tạo TelegramClient ở main → tạo trong worker thread:
client = TelegramClient(session_path, api_id, api_hash)
```
**Chức năng:** TelegramClient cần event loop riêng nên chỉ tạo trong thread của phiên → tránh crash. Gọi là **lazy initialization**.

---

### 3.3. SSE — đẩy tiến độ real-time về trình duyệt (app.py)

```python
return Response(stream_with_context(generate()),
                mimetype="text/event-stream")   # SSE
```
**Chức năng:** Server chủ động "đẩy" log/tiến độ liên tục về web (progress bar chạy live) mà không cần refresh. Gọi là **Server-Sent Events**.

#### Deep link bền vững — đổi bot link cũ vẫn sống
```python
@app.route("/d/<token>")
def deep_redirect(token):
    target = f"https://t.me/{username}?start={token}"   # redirect sang bot HIỆN TẠI
```
**Chức năng:** Link đi qua web trung gian rồi mới tới bot → đổi bot chỉ cần đổi config, link cũ không chết. Gọi là **indirection / redirect layer**.

---

### 3.4. Phương pháp NHẬN BÀI (nhận media qua bot — handlers.py)

#### Chỉ nhận trong private chat
```python
if not msg or update.effective_chat.type != "private":
    return   # bỏ qua nếu không phải chat riêng
```
**Chức năng:** Bot chỉ xử lý media gửi trong chat riêng → tránh tự kích hoạt khi bot là admin trong forum đích.

#### Trích thông tin file từ mọi loại media
```python
def extract_file_info(msg):
    if msg.photo:  return {"file_id": msg.photo[-1].file_id, "file_type": "photo", ...}
    if msg.video:  return {"file_id": msg.video.file_id, "file_type": "video", ...}
    # document / audio / voice / video_note / animation / sticker
```
**Chức năng:** Nhận diện loại media và lấy `file_id`, tên, dung lượng, thumbnail.

#### Gom album theo `media_group_id` (debounce)
```python
mgid = msg.media_group_id
if mgid:
    if entry and entry.get("task"):
        entry["task"].cancel()          # hủy timer cũ
    entry["msg_ids"].append(msg.message_id)
    entry["task"] = asyncio.create_task(_flush_album(key, ctx, user))  # chờ 1.5s
```
**Chức năng:** Telegram gửi album thành nhiều tin rời. Mỗi tin đến thì hủy timer cũ, đặt timer 1.5s mới → hết 1.5s không có tin nào nữa thì gom cả cụm thành 1 link. Kỹ thuật **debounce**.

---

### 3.5. Phương pháp FILE → LINK

#### Sinh token số ngẫu nhiên an toàn
```python
def generate_numeric_token(length=16):
    first = secrets.choice("123456789")   # số đầu 1-9, tránh số 0
    rest  = "".join(secrets.choice(string.digits) for _ in range(length - 1))
    return first + rest
```
**Chức năng:** Tạo mã token duy nhất kiểu `7754133249527383` (dùng `secrets` — khó đoán).

#### Lưu message_id (KHÔNG lưu file) → tạo link
```python
token = generate_numeric_token(16)
create_media_album(token, user.id, [msg.message_id], msg.caption or "")
url = build_share_url(token)
```
**Chức năng:** Lưu `message_id` bài gốc gắn với token. Điểm hay: lưu message_id thay vì file → khi serve dùng `copy_messages` giữ nguyên caption + premium emoji.

#### 2 chế độ link (web bền vững / bot trực tiếp)
```python
def build_share_url(token):
    if LINK_MODE == "web" and BASE_URL:
        return f"{BASE_URL}/d/{token}"          # web → redirect sang bot
    return f"https://t.me/{BOT_USERNAME}?start={token}"   # thẳng tới bot
```
**Chức năng:** Chế độ "web" trỏ qua server rồi mới tới bot → đổi bot link cũ vẫn sống.

#### Serve lại bằng `copy_messages` (3 lớp fallback)
```python
await ctx.bot.copy_messages(chat_id=chat_id, from_chat_id=src_chat_id,
                            message_ids=src_msg_ids, protect_content=protect)
# lỗi → forward_messages → cuối cùng từng tin một
```
**Chức năng:** Copy tin gốc về cho user (không hiện "Forwarded from"). 3 lớp: `copy_messages` → `forward_messages` → từng tin.

---

### 3.6. CÁCH LƯU METADATA (SQLite — models.py)

#### Bảng chính lưu link/album
```sql
CREATE TABLE media_albums (
    token         TEXT UNIQUE NOT NULL,   -- mã link
    src_chat_id   INTEGER,                -- chat nguồn
    src_msg_ids   TEXT,                   -- JSON [101,102,103]
    file_ids      TEXT,                   -- JSON media nhận trực tiếp
    expires_at    REAL,                   -- hết hạn
    max_views     INTEGER DEFAULT 0,      -- giới hạn xem
    allow_forward INTEGER DEFAULT 1,      -- cho forward hay không
    access_count  INTEGER DEFAULT 0       -- đếm lượt xem
);
```

#### Lưu list bằng JSON (SQLite không có kiểu mảng)
```python
_json.dumps(src_msg_ids)       # [101,102,103] → "[101,102,103]" khi ghi
_json.loads(d["src_msg_ids"])  # đọc ngược lại thành list
```
**Chức năng:** SQLite không lưu mảng → chuyển list thành chuỗi JSON, đọc ra thì parse ngược.

#### WAL mode — nhiều thread đọc/ghi an toàn
```python
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
```
**Chức năng:** Bật **WAL (Write-Ahead Logging)** → bot + web + forwarder đa luồng vẫn đọc/ghi DB an toàn.

#### UPSERT — có thì update, chưa có thì insert
```sql
INSERT INTO topics (...) VALUES (...)
ON CONFLICT(source_chat_id, source_topic_id) DO UPDATE SET ...
```
**Chức năng:** 1 lệnh tự xử lý cả 2 trường hợp mới/cũ → không cần check trước.

#### Soft delete — xóa mềm
```python
conn.execute("UPDATE media_albums SET is_active=0 WHERE token=?", (token,))
```
**Chức năng:** "Xóa" bằng đặt `is_active=0` thay vì xóa thật → dữ liệu vẫn còn, khôi phục được.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **`file_id`** | Mã file Telegram cấp, gửi lại mà không cần upload |
| **Debounce** | Chờ im lặng 1 khoảng rồi mới xử lý (gom album) |
| **`copy_messages`** | Copy tin, KHÔNG hiện "Forwarded from" |
| **JSON string** | Lưu list/mảng dưới dạng chuỗi trong 1 cột DB |
| **WAL mode** | Chế độ SQLite cho nhiều luồng đọc/ghi cùng lúc |
| **UPSERT** | Insert hoặc Update trong 1 lệnh (`ON CONFLICT`) |
| **Soft delete** | Xóa mềm — đánh dấu `is_active=0` |

---

### 3.7. Phương pháp RESUME (tiếp tục từ chỗ dừng — state.py + core.py)

#### Lưu ID cuối cùng đã xử lý vào file
```python
def save_last_id(key, mid):
    with open(f"{STATE_FILE}_{key}.txt", "w") as f:
        f.write(str(mid))
```

#### Đọc lại ID cũ, chỉ lấy tin MỚI HƠN
```python
last_id = load_last_id(key)
if last_id:
    start_msg_id = max(start_msg_id or 0, last_id)
min_id = (start_msg_id - 1) if start_msg_id else 0
async for msg in client.iter_messages(src_entity, min_id=min_id, reverse=True):
```
**Chức năng:** Chạy lại thì dùng `min_id` → Telegram chỉ trả tin có ID lớn hơn → bỏ qua toàn bộ tin đã forward.

#### Lưu liên tục trong lúc chạy
```python
count += n
last_id_buf = last_mid
save_last_id(topic_state_key, last_id_buf)   # lưu ngay sau mỗi batch
```
**Chức năng:** Crash/dừng giữa chừng → chạy lại nối đúng chỗ, chỉ mất tối đa 1 batch.

#### State kép — file (tương thích CLI) + SQLite (cho web)
```python
def save_session_meta(...):
    with open(path, "w") as f:      # 1) ghi file JSON
        json.dump(data, f)
    _db_upsert_session(data)        # 2) mirror vào SQLite
```
**Chức năng:** Lưu 2 nơi — file để tool CLI cũ đọc được, DB để web hiển thị. Gọi là **dual persistence**.

Cốt lõi: resume = "lưu ID cuối + lần sau dùng `min_id` bỏ qua tin cũ" — gọi là **checkpoint / high-water mark**.

---

### 3.8. Phương pháp CHECK JOIN (force-join — membership.py)

#### Gate — cổng chặn đặt đầu mọi handler
```python
async def gate(update, ctx) -> bool:
    ok = await check_user(ctx.bot, user.id)
    if ok: return True
    # chưa join → gửi nút "Tham gia kênh" + chặn
    return False
# Dùng: mọi lệnh mở đầu bằng:  if not await gate(update, ctx): return
```
**Chức năng:** 1 hàm "cổng gác" gọi đầu mọi handler. Gọi là **gate / guard pattern**.

#### Hỏi Telegram: user có trong kênh không
```python
cm = await bot.get_chat_member(chat_id=channel, user_id=user_id)
is_in = cm.status in {MEMBER, ADMINISTRATOR, OWNER}
```

#### Cache TTL — không hỏi API mỗi tin nhắn
```python
_cache[user_id] = {"ok": ok, "ts": time.time()}
check_sec = _get_check_sec() if entry["ok"] else _NON_MEMBER_TTL  # member 5 phút, non-member 60s
```
**Chức năng:** Nhớ kết quả trong RAM, tránh spam API. Gọi là **caching với TTL**.

#### Fail-open — cấu hình sai thì CHO QUA
```python
except Exception as e:
    if "not found" in msg or "invalid" in msg or "no rights" in msg:
        return True   # fail-open: không khóa nhầm toàn bộ user
```
**Chức năng:** Bot không vào được kênh (admin cấu hình sai) → cho user qua thay vì khóa hết. Gọi là **fail-open**.

#### Pending token — nhớ link user bấm trước khi bị chặn
```python
set_pending_token(user.id, token)                 # lúc bị chặn
token = pop_pending_token(user.id)                # sau khi join + bấm "Kiểm tra lại"
if token: await _serve_album(update, ctx, album)  # serve luôn media đang chờ
```
**Chức năng:** User bấm link nhưng chưa join → lưu token. Join xong tự gửi media luôn.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **Checkpoint / high-water mark** | Lưu mốc ID cuối đã xử lý để resume |
| **`min_id`** | Tham số Telethon: chỉ lấy tin có ID lớn hơn |
| **Dual persistence** | Lưu song song 2 nơi (file + DB) |
| **Gate / guard pattern** | Hàm chặn đặt đầu handler, chưa đủ điều kiện thì dừng |
| **`get_chat_member`** | API kiểm tra user có trong kênh không |
| **Cache TTL** | Nhớ kết quả 1 khoảng thời gian rồi mới hỏi lại |
| **Fail-open** | Gặp lỗi thì cho qua (thay vì khóa) |
| **Pending token** | Nhớ hành động đang chờ để làm tiếp sau |

---

### 3.9. BACKUP tự động (backup.py)

#### SQLite Backup API — copy DB an toàn khi đang ghi
```python
src = sqlite3.connect(src_db); dst = sqlite3.connect(dst_db)
with dst:
    src.backup(dst)   # API riêng, không lỗi dù DB đang được ghi
```

#### Rotation — tự xóa backup cũ
```python
cutoff = time.time() - KEEP_DAYS * 86400
if os.path.getmtime(fpath) < cutoff:
    os.remove(fpath)   # xóa file cũ hơn 7 ngày
```
**Chức năng:** Giữ backup N ngày, tự dọn file cũ. Gọi là **retention / rotation**.

#### Loại trừ file nhạy cảm khỏi backup
```python
# KHÔNG backup session_main.session (chứa thông tin đăng nhập)
if fname.endswith((".txt", ".json")):
    z.write(...)
```
**Chức năng:** Bỏ file `.session` (credential) ra khỏi zip → tránh lộ tài khoản.

#### Idempotent scheduler — gọi nhiều lần cũng chỉ chạy 1
```python
def start_backup_scheduler():
    global _scheduler_started
    if _scheduler_started: return False   # đã chạy rồi → bỏ qua
    _scheduler_started = True
```
**Chức năng:** Dù gọi bao nhiêu lần cũng chỉ 1 thread backup. Gọi là **idempotent**.

---

### 3.10. XỬ LÝ CAPTION tinh vi (link_sender.py)

#### Cắt caption theo UTF-16 giữ nguyên entities
```python
def _utf16_len(s):
    return len(s.encode("utf-16-le")) // 2   # Telegram tính offset theo UTF-16
```
**Chức năng:** Telegram giới hạn caption 1024, tính vị trí theo **UTF-16** (emoji = 2 đơn vị). Cắt theo UTF-16 để entity không lệch.

#### Dịch offset entity khi chèn text vào trước
```python
def _shift_entities(entities, offset_utf16):
    e2.offset = e.offset + offset_utf16   # đẩy vị trí theo phần thêm vào
```
**Chức năng:** Ghép template + caption gốc phải dịch vị trí entity → định dạng không lệch.

#### Edit caption SAU khi gửi (ổn định premium emoji)
```python
sent = await client.send_file(dst, file=preview, caption=full_cap,
                              formatting_entities=None)  # gửi trước
await asyncio.sleep(0.35)
await edit_caption_safe(client, dst, sent.id, text, entities)  # rồi edit gắn entities
```
**Chức năng:** Gửi media với caption thường trước, rồi edit lại gắn entities → giữ premium emoji ổn định hơn.

#### Chọn item album có caption "xịn" nhất
```python
premium = sum(1 for e in ents if isinstance(e, MessageEntityCustomEmoji))
score = premium*1000 + len(ents)*10 + len(text)   # ưu tiên premium emoji
```
**Chức năng:** Album nhiều ảnh caption khác nhau → chọn ảnh nhiều premium emoji + entity nhất làm caption chính.

#### Preview nhẹ — chỉ tải thumbnail, không tải cả video
```python
data = await client.download_media(msg, file=bytes, thumb=best[0])  # chỉ ảnh thumb
```
**Chức năng:** Link-mode gửi ảnh preview thay vì cả video nặng → nhanh, ít băng thông.

---

### 3.11. WEB AUTH — đăng nhập Telethon nhiều bước (web_auth.py)

#### Chạy code async từ thread khác qua `run_coroutine_threadsafe`
```python
self._loop = asyncio.new_event_loop()
threading.Thread(target=self._loop.run_forever, daemon=True).start()
def _run(self, coro, timeout=60):
    fut = asyncio.run_coroutine_threadsafe(coro, self._loop)  # gửi coro vào loop kia
    return fut.result(timeout=timeout)
```
**Chức năng:** Flask đồng bộ, Telethon bất đồng bộ → giữ 1 event loop riêng ở thread khác, đẩy lệnh async sang rồi chờ kết quả.

#### Login nhiều bước có state (phone → code → 2FA)
```python
try:
    await self._client.sign_in(self._phone, code, phone_code_hash=self._phone_hash)
except SessionPasswordNeededError:
    return {"ok": True, "need_password": True}   # cần bước 2FA
```
**Chức năng:** Đăng nhập 3 bước qua web, giữ `phone_code_hash` giữa các bước, bắt lỗi 2FA để hỏi mật khẩu.

---

### 3.12. Xử lý lỗi & pin (core.py)

#### Phân loại lỗi vĩnh viễn vs tạm thời
```python
PERMANENT_ERROR_NAMES = {"MessageIdInvalidError", "MediaEmptyError", ...}
def is_permanent_error(exc):
    return type(exc).__name__ in PERMANENT_ERROR_NAMES
# vĩnh viễn → skip luôn; tạm thời → retry
```
**Chức năng:** Lỗi "tin đã xóa" (vĩnh viễn) → bỏ qua ngay; lỗi mạng (tạm thời) → thử lại.

#### Exponential backoff — chờ tăng dần khi retry
```python
backoff = 2 * (attempt + 1)   # 2s, 4s, 6s... mỗi lần thử lại chờ lâu hơn
await asyncio.sleep(backoff)
```
**Chức năng:** Lỗi tạm thời → chờ lâu dần mỗi lần retry, giảm áp lực server.

#### id_map — ánh xạ ID nguồn → ID đích (để clone pin)
```python
for s, d in zip(src_ids, dest_ids):
    id_map[s] = d   # nhớ tin nguồn X → tin đích Y
```
**Chức năng:** Nhớ tin nào ở nguồn thành tin nào ở đích → dùng để clone lại pin đúng chỗ.

#### Clone pin theo thứ tự ngược
```python
for src_id in reversed(pinned_src_ids):   # pin ngược để tin đầu nằm trên cùng
    await pin_message(client, dst_entity, id_map[src_id], ...)
```
**Chức năng:** Telegram xếp pin mới nhất lên trên → pin ngược thứ tự để giữ đúng thứ tự nguồn.

#### Pin qua Bot API trước, Telethon sau (graceful fallback)
```python
# 1. Thử Bot API (ít FloodWait)
await bot.pin_chat_message(...)
# 2. Lỗi → fallback Telethon; FloodWait > 30s thì bỏ qua
```
**Chức năng:** Ưu tiên cách ít bị giới hạn, hỏng thì chuyển cách khác. Gọi là **graceful fallback**.

#### Relink — regex thay link bot cũ → mới, giữ token
```python
pattern = re.compile(r'https?://t\.me/OLDBOT\?start=([A-Za-z0-9_-]+)')
token = pattern.search(text).group(1)   # bắt token trong link cũ
new_text = pattern.sub(new_url, text)    # thay bằng link bot mới
```
**Chức năng:** Đổi bot → quét forum đích, tìm link cũ, thay bằng link mới nhưng giữ nguyên token → link cũ không chết.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **SQLite Backup API** | Copy DB an toàn khi đang ghi (`src.backup(dst)`) |
| **Retention / Rotation** | Giữ N ngày, tự xóa file cũ |
| **Idempotent** | Gọi nhiều lần cũng cho 1 kết quả (không nhân đôi) |
| **UTF-16 offset** | Cách Telegram tính vị trí entity (emoji = 2 đơn vị) |
| **`run_coroutine_threadsafe`** | Cầu nối code async ↔ thread đồng bộ |
| **Permanent vs transient error** | Lỗi không cứu được (skip) vs lỗi tạm (retry) |
| **Exponential backoff** | Retry chờ lâu dần (2s, 4s, 6s...) |
| **Graceful fallback** | Cách chính hỏng → tự chuyển cách phụ |
| **id_map** | Ánh xạ ID nguồn ↔ ID đích để clone pin |

---

## Tool 4 — Auto xếp bài + forward đa kênh (v20, dùng Pyrogram)

Userbot: forward bài vào Saved Messages → tool tự xen ads → forward ra nhiều kênh theo topic. Dùng **Pyrogram** (không phải Telethon). Dưới đây chỉ liệt kê phương pháp MỚI (batch/TokenBucket/split/FloodWait retry/premium emoji đã có ở Tool 1-3).

### 4.1. Slot-based state machine — nhiều batch song song
```python
state = {"slots": [make_slot()], ...}
def active_slot():  return state["slots"][-1]   # slot đang gom bài
def waiting_slot():                             # slot đang chờ chọn kênh
    for s in state["slots"]:
        if s["awaiting_channel"]: return s
```
**Chức năng:** Mỗi "batch" là 1 slot độc lập. Đang forward slot cũ (chạy nền) thì user vẫn gom bài mới vào slot mới → nhiều batch chồng nhau không lẫn. Gọi là **state machine đa slot**.

### 4.2. Global flood gate — chờ chung, không cộng dồn thời gian
```python
async def flood_wait_globally(seconds, source=""):
    async with _flood_gate:
        remaining = _flood_until - now
        if remaining > 0:
            await asyncio.sleep(remaining)   # coroutine sau chỉ chờ NỐT
            return                           # KHÔNG set lại _flood_until
        _flood_until = now + seconds
        await asyncio.sleep(seconds)
```
**Chức năng:** Khác TokenBucket (giới hạn tốc độ). Đây là cổng chờ chung: 1 coroutine dính FloodWait → mọi coroutine khác cùng chờ tới đúng mốc `_flood_until`, không mỗi thằng chờ riêng gây cộng dồn. Gọi là **coordinated global backoff**.

### 4.3. Thuật toán xen ads vào content (3 mode)
```python
# normal: chia content thành (số_ads + 1) nhóm đều, chèn 1 ads giữa
groups = total_ads + 1
base, extra = divmod(n, groups)
sizes = [base + (1 if g < extra else 0) for g in range(groups)]
# xdone: ads xen đều GIỮA các bài
# zdone: ads TRƯỚC, content SAU
```
**Chức năng:** Dùng `divmod` rải ads đều vào giữa content theo 3 kiểu. Gọi là **interleaving / thuật toán phân phối**.

### 4.4. Round-robin có nhớ trạng thái (luân phiên kênh theo topic)
```python
def pick_next_rr(topic_title, cmds):
    rr = load_topic_rr()               # đọc từ file
    idx = (rr.get(key, -1) + 1) % len(cmds)
    rr[key] = idx; save_topic_rr(rr)   # lưu lại
    return cmds[idx]
```
**Chức năng:** 1 topic map tới nhiều kênh → mỗi lần chọn kênh kế tiếp xoay vòng, nhớ vị trí qua file để lần sau tiếp tục đúng chỗ. Gọi là **persistent round-robin**.

### 4.5. Dò topic từ bài đã forward (trace fwd_from bằng raw API)
```python
raw = await client.invoke(fn.messages.GetMessages(id=[...]))
fwd = rm.fwd_from
sp, smid = fwd.saved_from_peer, fwd.saved_from_msg_id   # truy ngược nguồn gốc
og  = await client.invoke(fn.channels.GetMessages(channel=inch, id=[smid]))
top_id = og.messages[0].reply_to.reply_to_top_id        # → topic gốc
```
**Chức năng:** Từ bài trong Saved Messages, truy ngược `saved_from_peer` → lấy bài gốc → đọc topic gốc → tự biết bài thuộc topic nào. Gọi là **forward-origin tracing**.

### 4.6. Config bằng file text người sửa tay + directive
```python
# topic_map.txt:
#   vitamin = pro          ← map topic → kênh
#   @xepbai = off          ← directive điều khiển hành vi
#   @xepbaiwhite = pro,real
def get_xepbai_mode(): # đọc directive @xepbai
def load_topic_txt():  # đọc các dòng map thường (bỏ dòng @)
```
**Chức năng:** Cấu hình bằng file `.txt` cho người không biết code sửa tay; phân biệt dòng map thường vs dòng `@directive` điều khiển. Gọi là **human-editable config + directives**.

### 4.7. Tự sinh lệnh /tap từ tên kênh
```python
def get_cmd_key(title, alias=""):
    parts = title.strip().split()       # "🔥 Kênh ABC PRO" → lấy từ cuối
    return _strip_junk(parts[-1]).lower()   # → lệnh /pro
def build_channel_commands(channels):
    groups.setdefault(key, []).append(ch)   # gom kênh cùng key
    lines.append(f"/{key}   ({titles})")     # thành nút /pro tap được
```
**Chức năng:** Tự biến tên kênh thành lệnh `/pro`, `/real`… để tap forward nhanh; gom nhiều kênh cùng tên thành 1 lệnh. Gọi là **auto command generation**.

### 4.8. Quiescence barrier — chờ album fetch xong trước khi đếm
```python
slot["_album_pending"] += 1              # lúc nhận album: tăng đếm
# update_menu: chờ đếm về 0 rồi mới build sequence
for _ in range(30):  # tối đa 15s
    if slot.get("_album_pending", 0) <= 0: break
    await asyncio.sleep(0.5)
```
**Chức năng:** Album fetch chậm (async), single msg tới nhanh → nếu đếm ngay sẽ thiếu bài. Dùng biến đếm chờ "lặng" hết album mới xử lý. Gọi là **quiescence barrier / pending counter**.

### 4.9. Bounded concurrency bằng Semaphore
```python
sem = asyncio.Semaphore(FWD_MAX_CONCURRENT_CHANNELS)  # tối đa 2 kênh cùng lúc
async def _fwd_one(ch):
    async with sem: ...
await asyncio.gather(*[_fwd_one(ch) for ch in results])
```
**Chức năng:** Forward nhiều kênh song song nhưng chỉ 2 kênh cùng lúc (Tool 3 dùng thread, tool này dùng `asyncio.Semaphore` — nhẹ hơn). Gọi là **bounded concurrency**.

### 4.10. Bảo trì nền có kiểm tra "user đang bận"
```python
async def task_auto_clean_dead():
    while True:
        await asyncio.sleep(DEAD_CHECK_INTERVAL_SEC)
        while _user_busy() and waited < 600:   # đợi user rảnh mới chạy
            await asyncio.sleep(60)
        await cmd_checkchan(auto_clean=True, silent=True)
```
**Chức năng:** Task nền tự dọn kênh chết mỗi 6h, nhưng hoãn nếu user đang gom/forward bài → không làm phiền. Gọi là **deferred background maintenance**.

### 4.11. Phân loại kênh: chết hẳn vs không rõ (không xóa nhầm)
```python
DEAD_CHANNEL_ERRORS  = (ChannelInvalid, ChannelPrivate, PeerIdInvalid, ...)  # xóa
SKIP_NOT_DEAD_ERRORS = (ChatWriteForbidden, ChatAdminRequired)               # skip
# FloodWait/network → "unknown" → GIỮ LẠI, thử lại sau
```
**Chức năng:** Chỉ xóa kênh khi lỗi chắc chắn chết; FloodWait/mạng → xếp "không rõ", giữ lại. Tránh xóa nhầm. Gọi là **liveness classification** (giống permanent/transient nhưng thêm nhóm "unknown").

### 4.12. Import folder Telegram (chatlist invite) + auto-sync
```python
result = await app.invoke(raw_fn.chatlists.CheckChatlistInvite(slug=slug))
chats  = result.chats   # tất cả kênh trong folder
# task_auto_sync_folders: tự sync mỗi 1h → kênh mới trong folder tự thêm
```
**Chức năng:** Nhập nguyên 1 folder Telegram (link `addlist/xxx`), tự đồng bộ định kỳ để kênh mới tự vào. Gọi là **chatlist import + auto-sync**.

### 4.13. Command aliasing (nhiều tên lệnh → 1 hành động)
```python
COMMAND_ALIASES = {"/addchan": "/add", "/checkchan": "/check", ...}
def normalize_command(text):   # /addchan @x → /add @x
```
**Chức năng:** Nhiều tên lệnh cùng trỏ về 1 hành động. Gọi là **command aliasing**.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **State machine đa slot** | Nhiều batch độc lập chạy chồng nhau |
| **Global flood gate** | Cổng chờ chung, mọi coroutine chờ tới 1 mốc, không cộng dồn |
| **Interleaving (divmod)** | Rải ads đều vào giữa content |
| **Persistent round-robin** | Luân phiên kênh, nhớ vị trí qua file |
| **Forward-origin tracing** | Truy ngược bài forward về nguồn/topic gốc |
| **Human-editable config + directives** | File .txt người sửa tay, có dòng `@lệnh` điều khiển |
| **Auto command generation** | Tự sinh lệnh /tap từ tên kênh |
| **Quiescence barrier** | Chờ tác vụ async "lặng" hết rồi mới xử lý |
| **Bounded concurrency (Semaphore)** | Giới hạn số việc song song |
| **Deferred maintenance** | Bảo trì nền, hoãn khi user bận |
| **Liveness classification** | Chia kênh: chết / skip / không rõ để tránh xóa nhầm |
| **Chatlist import** | Nhập cả folder Telegram, auto-sync |
| **Command aliasing** | Nhiều tên lệnh → 1 hành động |

---

## ⚠️ Nhược điểm & cách khắc phục (Tool 4 — FloodWait)

### Vấn đề
Khi Telegram bắt chờ (FloodWait) 10-20s, tool **mất bài (album) hoặc mất mapping topic**. Trong khi đường *forward* chịu được (có global flood gate), thì đường *nhận bài* và *dò topic* lại không.

### Nguyên nhân
Pyrogram mặc định `sleep_threshold = 10s`:
- FloodWait ≤ 10s: Pyrogram tự ngủ → OK.
- FloodWait > 10s (vd 20s): **ném exception** ra ngoài.

Hai chỗ sau bắt lỗi bằng `except Exception` chung chung, không đọc `e.value`, nên FloodWait lớn → rớt:

```python
# CHỖ 1 — dò topic: FloodWait rơi vào except → trả None → MẤT MAPPING
except Exception as e:
    return (None, None, None)

# CHỖ 2 — fetch album: retry chỉ ngủ 0.5/1/2s cố định (< 10-20s) → MẤT BÀI
for attempt, delay in enumerate([0.5, 1.0, 2.0]):
    ...
    except Exception as e:      # không đọc e.value
        log("WARN", ...)
if not album:
    return                      # bỏ nguyên chùm album
```
Bài single (text/ảnh lẻ) KHÔNG rớt vì chỉ `append(msg.id)`, không gọi API. Chỉ album + mapping rớt vì cần gọi API phụ.

### Cách sửa (hybrid — đã áp dụng)

**Bước 1 — nâng ngưỡng tự nuốt FloodWait toàn cục (1 dòng):**
```python
app = Client("test_session", api_id=API_ID, api_hash=API_HASH,
             sleep_threshold=60)   # Pyrogram tự ngủ với FloodWait <=60s ở MỌI lệnh
```

**Bước 2 — thêm retry đọc `e.value` ở 2 chỗ dễ rớt (chịu cả khi >60s):**
```python
# resolve_forward_topic: bọc vòng for + bắt FloodWait riêng
for attempt in range(FWD_MAX_RETRY):
    try:
        ... # gọi 3 raw API
    except FloodWait as e:
        await flood_wait_globally(e.value + 3, source="topic_detect")  # chờ qua gate chung

# get_media_group: delay tăng dần + bắt FloodWait đọc e.value
for attempt, delay in enumerate([0.5, 1.0, 2.0, 4.0, 8.0, 8.0]):
    await asyncio.sleep(delay)
    try:
        album = await client.get_media_group(SAVED_MESSAGES, msg.id)
        ...
    except FloodWait as e:
        await flood_wait_globally(e.value + 3, source="album_fetch")   # ngủ đúng số giây
```

**Vì sao hybrid tối ưu:** `sleep_threshold=60` xử lý 99% trường hợp chỉ với 1 dòng (mọi lệnh tự khỏi). Còn 2 khối `except FloodWait` là lớp phòng thủ cho trường hợp hiếm >60s, và định tuyến qua `flood_wait_globally` để khi 2 kênh chạy song song không cộng dồn thời gian chờ.

| Thuật ngữ | Nghĩa dễ hiểu |
|---|---|
| **`sleep_threshold`** | Ngưỡng Pyrogram tự ngủ nuốt FloodWait thay vì ném lỗi |
| **`e.value`** | Số giây Telegram yêu cầu chờ trong FloodWait |
| **Lớp phòng thủ nhiều tầng** | Ngưỡng toàn cục + retry riêng cho ca hiếm |

---
