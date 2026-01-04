import csv
import time
import requests
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime

ALBUM_ID = "_dvRrSJ0oEMCI-DuL_goyb1Vu4aVJ9kC94pxeAEw"
COOKIE = 'token=NkRBMjdFQTI5OTkyRDAxRTEzOTBCRUY3NkFDMDNERDY3REEzNjU1QzYwODRCOTJBNTA1MDk5QTJCQ0Q1ODdEOUE1QTFGRkM1MjM4MkNFMEY1REUzOUUyQTc5MzQ2NjUy; client_type=net; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22_drSrS9leVbTDK5ed_ePKAuTJV0HKseoxA7zbYwg%22%2C%22first_id%22%3A%2219b1e200276176-0f49e2a47c74068-26061a51-1600000-19b1e200279b5d%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%A4%BE%E4%BA%A4%E7%BD%91%E7%AB%99%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fopen.weixin.qq.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfbG9naW5faWQiOiJfZHJTclM5bGVWYlRESzVlZF9lUEtBdVRKVjBIS3Nlb3hBN3piWXdnIiwiJGlkZW50aXR5X2Nvb2tpZV9pZCI6IjE5YjFlMjAwMjc2MTc2LTBmNDllMmE0N2M3NDA2OC0yNjA2MWE1MS0xNjAwMDAwLTE5YjFlMjAwMjc5YjVkIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22_drSrS9leVbTDK5ed_ePKAuTJV0HKseoxA7zbYwg%22%7D%2C%22%24device_id%22%3A%2219b1e200276176-0f49e2a47c74068-26061a51-1600000-19b1e200279b5d%22%7D; JSESSIONID=5C21CC1367474A228A59FFB6301F940F'

OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "szwego_products.csv")

header = ["productId", "name", "description", "price", "status", "brand", "category", "photos"]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": COOKIE,
    "Referer": f"https://www.szwego.com/static/index.html#shop_detail/{ALBUM_ID}",
}

session = requests.Session()
all_rows = []
timestamp_val = int(time.time() * 1000)

MIN_PHOTOS = 4
PHOTO_YEAR = "2025"
MIN_DESCRIPTION_LEN = 80
MIN_DESCRIPTION_WORDS = 5

DEBUG_GOODS_ID = "_d6KrS_ZEvcxnEdxSFmnEo-WsZLciEwkr2qZ3IXw"


def _parse_year_from_date_text(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(\d{4})[./-]\d{2}[./-]\d{2}", text.strip())
    return m.group(1) if m else ""


def _parse_year_from_item_fields(item: dict) -> str:
    for k in (
        "createTime",
        "create_time",
        "createdTime",
        "created_time",
        "uploadTime",
        "upload_time",
        "time",
        "date",
    ):
        v = item.get(k)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            try:
                ts = float(v)
                if ts > 10_000_000_000:
                    ts /= 1000.0
                return str(datetime.fromtimestamp(ts).year)
            except Exception:
                pass
        if isinstance(v, str):
            y = _parse_year_from_date_text(v)
            if y:
                return y
    return ""


def _fetch_year_from_goods_page(session: requests.Session, url: str) -> str:
    if not url:
        return ""
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one('div[class*="shopinfo_time_text"]')
        if not el:
            return ""
        return _parse_year_from_date_text(el.get_text(strip=True))
    except Exception:
        return ""


def get_item_year(item: dict) -> str:
    y = _parse_year_from_item_fields(item)
    if y:
        return y

    for k in ("goodsUrl", "goods_url", "detailUrl", "detail_url", "url", "link"):
        url = item.get(k)
        if isinstance(url, str) and url.strip():
            y = _fetch_year_from_goods_page(session, url.strip())
            if y:
                return y

    return ""

started_at = time.perf_counter()

skip_reasons: dict[str, int] = {}


def _skip(reason: str, goods_id: str, extra: str = "") -> None:
    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
    if DEBUG_GOODS_ID and goods_id == DEBUG_GOODS_ID:
        print(f"SKIP[{reason}] goods_id={goods_id} {extra}")

seen_photo_keys: dict[tuple[str, ...], int] = {}
seen_by_goods_id: dict[str, dict[str, object]] = {}
dups_by_photo = 0
dups_by_id = 0
replaced_by_id = 0

page_idx = 1
total_items = 0          # всего товаров от API
total_imgs = 0           # всего фоток по этим товарам
saved_items = 0          # сколько реально ушло в CSV

try:
    while True:
        page_started_at = time.perf_counter()

        params = {
            "albumId": ALBUM_ID,
            "searchValue": "",
            "searchImg": "",
            "startDate": "",
            "endDate": "",
            "sourceId": "",
            "requestDataType": "",
            "transLang": "en",
            "timestamp": timestamp_val,
        }

        r = session.get(
            "https://www.szwego.com/album/personal/image",
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        data = r.json()
        if not data.get("success"):
            print("API error:", data)
            break

        result = data["result"]
        items = result.get("items", [])
        if not items:
            print("Пустой ответ, стоп.")
            break

        page_items = 0
        page_imgs = 0

        for item in items:
            goods_id = item.get("goods_id", "")
            if not goods_id:
                goods_id = f"auto_{int(time.time() * 1000)}"

            # 1. откуда БЕРЁМ текст товара
            # подставь сюда реальное поле: title / remark / content / desc и т.п.
            raw_text = item.get("title", "") or ""

            # 2. если встречается 集合图 — пропускаем товар
            if "集合图" in raw_text:
                continue

            # 3. полный текст товара → description
            description = " ".join(
                raw_text.replace("\r", " ").replace("\n", " ").split()
            )

            imgs_src = item.get("imgsSrc", []) or []
            photos = [u.strip() for u in imgs_src if u and u.strip()]

            page_items += 1
            page_imgs += len(photos)

            # фильтр по количеству фоток - выгружаем от 4 фото
            if len(photos) < MIN_PHOTOS:
                _skip("few_photos", goods_id, f"photos={len(photos)}")
                continue

            item_year = get_item_year(item)
            if PHOTO_YEAR and item_year != PHOTO_YEAR:
                _skip("year_mismatch", goods_id, f"item_year={item_year!r}")
                continue

            if len(description) < MIN_DESCRIPTION_LEN:
                _skip("short_description", goods_id, f"len={len(description)}")
                continue

            if " " in description:
                words_count = len(description.split())
                if words_count < MIN_DESCRIPTION_WORDS:
                    _skip("few_words", goods_id, f"words={words_count}")
                    continue

            # фильтр MP4 файлов - пропускаем товары с видео
            has_mp4 = any(".mp4" in photo for photo in photos)
            if has_mp4:
                _skip("has_mp4", goods_id, "")
                continue

            # name не используем
            name = ""

            row = [
                goods_id,
                name,
                description,                           # ← здесь уже точно есть текст
                "",
                "",
                "",
                "",
                json.dumps(photos, ensure_ascii=False),
            ]

            row = [
                str(cell).replace("\r", " ").replace("\n", " ").strip()
                for cell in row
            ]

            photo_key = tuple(sorted(set(photos)))
            existing_photo_idx = seen_photo_keys.get(photo_key)
            if existing_photo_idx is not None:
                dups_by_photo += 1
                continue

            existing_by_id = seen_by_goods_id.get(goods_id)
            if existing_by_id is not None:
                dups_by_id += 1
                new_desc_len = len(row[2])
                old_desc_len = int(existing_by_id.get("desc_len") or 0)
                if new_desc_len > old_desc_len:
                    old_idx = int(existing_by_id["idx"])
                    old_photo_key = existing_by_id.get("photo_key")

                    if old_photo_key in seen_photo_keys:
                        del seen_photo_keys[old_photo_key]

                    if photo_key in seen_photo_keys:
                        seen_photo_keys[old_photo_key] = old_idx
                        continue

                    all_rows[old_idx] = row
                    seen_by_goods_id[goods_id] = {"idx": old_idx, "desc_len": new_desc_len, "photo_key": photo_key}
                    seen_photo_keys[photo_key] = old_idx
                    replaced_by_id += 1
                continue

            all_rows.append(row)
            saved_items += 1

            new_idx = len(all_rows) - 1
            seen_photo_keys[photo_key] = new_idx
            seen_by_goods_id[goods_id] = {"idx": new_idx, "desc_len": len(row[2]), "photo_key": photo_key}

        total_items += page_items
        total_imgs += page_imgs

        page_elapsed = time.perf_counter() - page_started_at
        total_elapsed_now = time.perf_counter() - started_at
        print(
            f"Страница {page_idx}: от API товаров {page_items}, фото {page_imgs} "
            f"(всего {total_items} / {total_imgs}), в CSV прошло {saved_items} "
            f"[{page_elapsed:.2f}s | total={total_elapsed_now:.2f}s]"
        )

        # Сохраняем после каждой страницы
        if all_rows:
            with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", lineterminator="\n")
                writer.writerow(header)
                writer.writerows(all_rows)
            print(f"  → Промежуточное сохранение: {len(all_rows)} товаров")

        pag = result.get("pagination") or {}
        if not pag.get("isLoadMore"):
            print("Больше страниц нет.")
            break

        timestamp_val = pag["pageTimestamp"]
        page_idx += 1
finally:
    total_elapsed = time.perf_counter() - started_at
    print(f"Время выполнения: {total_elapsed:.2f}s")

# Финальное сохранение
if all_rows:
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(all_rows)
    print(f"Финальное сохранение: {len(all_rows)} товаров")

print(
    f"Готово! От API пришло {total_items} товаров ({total_imgs} фото), "
    f"в CSV записано {saved_items} товаров с >= {MIN_PHOTOS} фото за {PHOTO_YEAR} год → {OUT_CSV}"
)

print(f"Дубли: по фото={dups_by_photo}, по id={dups_by_id}, заменено по id={replaced_by_id}")

if skip_reasons:
    print("Пропуски по причинам:")
    for k, v in sorted(skip_reasons.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k}: {v}")
