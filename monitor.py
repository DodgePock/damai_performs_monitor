import datetime
import json
import logging
import os
from copy import deepcopy
from pathlib import Path

import requests
from parsel import Selector

from settings import TARGET_SETTINGS, MESSPUSHER_CONFIG, PROXIES
from messpusher import Messpusher


logger = logging.getLogger(__name__)
ROOT_ABS_PATH = os.path.dirname(os.path.abspath(__file__))

def config_logging():
    log_file = os.path.join(ROOT_ABS_PATH, "monitor.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def get_proxies():
    if PROXIES==None or len(PROXIES)==0:
        return None
    # 当日分钟数对len(PROXIES)取模，选择代理
    current_minute = datetime.datetime.now().hour * 60 + datetime.datetime.now().minute
    proxy_index = current_minute % len(PROXIES)
    selected_proxy = PROXIES[proxy_index]
    logger.debug(f"Selected proxy: {selected_proxy}")
    proxies = {
        'http': selected_proxy,
        'https': selected_proxy
    }
    return proxies


def get_item_detail(target_item_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15'
    }
    url = 'https://detail.damai.cn/item.htm'
    params = {'id': target_item_id}
    proxies = get_proxies()
    try:
        r = requests.get(url=url, headers=headers, params=params, proxies=proxies, timeout=10)
        if r.status_code != 200:
            return None, f'获取网页失败，status_code:{r.status_code}'
        selector = Selector(r.text)
        detail_text = selector.css('div#dataDefault::text').get()
        if detail_text == None:
            return None, f'无法获取到网页中的项目详细信息'
        try:
            detail_json = json.loads(detail_text, strict=False)
        except Exception as e:
            return None, f'Json数据解析失败: {e}'
        return detail_json, "success"
    except Exception as e:
        return None, f'出现错误：{e}'
        

def get_detail_perform_briefs(item_detail):
    perform_briefs = {}
    try:
        for calendar_perform in item_detail['calendarPerforms']:
            for perform_base in calendar_perform['performBases']:
                for perform in perform_base['performs']:
                    perform_briefs[str(perform['performId'])] = {
                        'item_id': perform['itemId'],
                        'perform_id': perform['performId'],
                        'perform_name' : perform['performName'],
                        'perform_start_ts': perform['performDate']//1000
                    }
        return perform_briefs
    except:
        return None

def load_perform_brief_cache(item_id):
    file_path = Path(ROOT_ABS_PATH) / "perform_caches" / f"{item_id}.json"
    if not file_path.exists():
        return {}
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[WARN] Failed to load cache for item {item_id}: {e}")
        return {}
    
def save_perform_brief_cache(item_id: str, perform_briefs: dict) -> None:
    folder_path = Path(ROOT_ABS_PATH) / "perform_caches"
    file_path = folder_path / f"{item_id}.json"
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(perform_briefs, f, ensure_ascii=False, indent=4)
    except OSError as e:
        logger.error(f"[ERROR] Failed to save perform briefs for item {item_id}: {e}")


def check_perform_updates(item_id, curr_perform_briefs: dict) -> dict:
    prev_perform_briefs = load_perform_brief_cache(item_id)
    prev_keys = set(prev_perform_briefs.keys())
    curr_keys = set(curr_perform_briefs.keys())
    added_keys = curr_keys - prev_keys
    removed_keys = prev_keys - curr_keys
    added_performs = [curr_perform_briefs[k] for k in added_keys]
    removed_performs = [prev_perform_briefs[k] for k in removed_keys]
    has_added = bool(added_keys)
    has_removed = bool(removed_keys)
    has_update = has_added or has_removed
    return {
        "has_update": has_update,
        "has_added": has_added,
        "has_removed": has_removed,
        "added_performs": added_performs,
        "removed_performs": removed_performs,
    }

def get_keywords_matched_performs(performs, keywords):
    if not performs or not keywords:
        return []
    matched_performs = []
    for perform in performs:
        matched_keywords = [kw for kw in keywords if kw in perform['perform_name']]
        if matched_keywords:
            matched_perform = deepcopy(perform)
            matched_perform['matched_keywords'] = matched_keywords
            matched_performs.append(matched_perform)
    return matched_performs

def generate_push_content(performs):
    if not performs:
        return "没有匹配到任何演出"
    content = []
    for perform in performs:
        matched_keywords_str = '/'.join(perform.get('matched_keywords', []))
        content.append(f"{perform['perform_name']}\n"
                       f"https://detail.damai.cn/item.htm?id={perform['item_id']}\n"
                       f"keywords: {matched_keywords_str}\n")
    return "---------------------------\n".join(content)

def main():
    config_logging()
    for target_item_id, keywords in TARGET_SETTINGS.items():
        item_detail, msg = get_item_detail(target_item_id)
        if item_detail ==None:
            logger.info(f'Failed to get item details:{msg}')
            continue
        perform_briefs = get_detail_perform_briefs(item_detail)
        if perform_briefs==None:
            logger.info(f'Failed to get perform briefs')
            continue
        perform_update_info = check_perform_updates(target_item_id, perform_briefs)
        
        # 如果has_update为False，则不保存缓存
        # 如果has_update为True；如果没有匹配到关键词，则保存缓存且不发送通知
        # 如果has_update为True，且匹配到关键词，如果发送通知成功，则保存缓存，否则不保存缓存
        if perform_update_info['has_update']:
            keywords_matched_performs = get_keywords_matched_performs(perform_update_info['added_performs'], keywords)
            if keywords_matched_performs:
                logger.info(f"{len(keywords_matched_performs)} new performs matched keywords")
                push_title = f"大麦演出关键词匹配通知 - {len(keywords_matched_performs)}场演出"
                push_content = generate_push_content(keywords_matched_performs)
                messpusher = Messpusher(MESSPUSHER_CONFIG)
                push_result = messpusher.send_all(push_title, push_content)
                if push_result:
                    logger.info(f"Push notification sent successfully: {push_result}")
                    save_perform_brief_cache(target_item_id, perform_briefs)
                else:
                    logger.error("Failed to send push notification")
                    continue
            else:
                logger.info("No new performs matched keywords, skipping push notification")
                save_perform_brief_cache(target_item_id, perform_briefs)
        else:
            logger.info(f"No updates for item {target_item_id}, skipping cache save")

if __name__ == '__main__':
    main()
    