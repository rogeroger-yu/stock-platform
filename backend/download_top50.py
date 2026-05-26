"""Download Top 50 A-share stocks by market cap."""

import time
import akshare as ak
import pandas as pd
from app.data.fetcher import fetch_stock_daily
from app.data.store import save_stock_daily

# Top 50 A-share stocks by market cap (hardcoded for reliability)
TOP50 = [
    ("600519", "贵州茅台"), ("601398", "工商银行"), ("601288", "农业银行"),
    ("600036", "招商银行"), ("601166", "兴业银行"), ("000858", "五粮液"),
    ("600276", "恒瑞医药"), ("000001", "平安银行"), ("601318", "中国平安"),
    ("600900", "长江电力"), ("600030", "中信证券"), ("000333", "美的集团"),
    ("601888", "中国中免"), ("600809", "山西汾酒"), ("002594", "比亚迪"),
    ("601012", "隆基绿能"), ("600000", "浦发银行"), ("601601", "中国太保"),
    ("600016", "民生银行"), ("000568", "泸州老窖"), ("002714", "牧原股份"),
    ("600585", "海螺水泥"), ("000651", "格力电器"), ("601899", "紫金矿业"),
    ("600050", "中国联通"), ("002475", "立讯精密"), ("601668", "中国建筑"),
    ("600887", "伊利股份"), ("000002", "万科A"), ("601857", "中国石油"),
    ("600028", "中国石化"), ("601088", "中国神华"), ("002304", "洋河股份"),
    ("600104", "上汽集团"), ("000725", "京东方A"), ("601328", "交通银行"),
    ("600009", "上海机场"), ("002352", "顺丰控股"), ("600031", "三一重工"),
    ("601225", "陕西煤业"), ("000063", "中兴通讯"), ("600690", "海尔智家"),
    ("002415", "海康威视"), ("600309", "万华化学"), ("601138", "工业富联"),
    ("000538", "云南白药"), ("600048", "保利发展"), ("002230", "科大讯飞"),
    ("601919", "中远海控"), ("600196", "复星医药"),
]

def download_top50(start_date="20150101", end_date="20260526"):
    print(f"Downloading {len(TOP50)} stocks from {start_date} to {end_date}...")
    success = 0
    failed = 0
    for i, (code, name) in enumerate(TOP50, 1):
        try:
            df = fetch_stock_daily(code, start_date, end_date)
            path = save_stock_daily(df, code)
            success += 1
            print(f"[{i}/{len(TOP50)}] ✓ {name}({code}): {len(df)} rows")
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(TOP50)}] ✗ {name}({code}): {e}")
        time.sleep(0.3)
    print(f"\nDone. Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    download_top50()
