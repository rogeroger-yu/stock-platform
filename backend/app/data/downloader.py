"""批量下载 A 股数据的 CLI 脚本。"""

import argparse
import time

from app.data.fetcher import fetch_stock_list, fetch_stock_daily
from app.data.store import save_stock_daily, save_metadata


def download_all(
    start_date: str = "20150101",
    end_date: str = "20241231",
    max_stocks: int | None = None,
    delay: float = 0.3,
) -> None:
    """下载全部A股日线数据。

    Args:
        start_date: 起始日期 (YYYYMMDD).
        end_date: 结束日期 (YYYYMMDD).
        max_stocks: 最大下载数量（调试用），None=全部.
        delay: 请求间隔秒数.
    """
    print("Fetching stock list...")
    stock_list = fetch_stock_list()
    print(f"Found {len(stock_list)} stocks.")

    # Save metadata to sqlite
    save_metadata(stock_list)
    print("Metadata saved to SQLite.")

    codes = stock_list["code"].tolist()
    if max_stocks is not None:
        codes = codes[:max_stocks]

    success = 0
    failed = 0

    for i, code in enumerate(codes, 1):
        try:
            df = fetch_stock_daily(code, start_date, end_date)
            path = save_stock_daily(df, code)
            success += 1
            if i % 100 == 0 or i == len(codes):
                print(f"[{i}/{len(codes)}] Saved {code} -> {path} ({len(df)} rows)")
        except Exception as exc:
            failed += 1
            print(f"[{i}/{len(codes)}] FAILED {code}: {exc}")

        # Rate limiting
        time.sleep(delay)

    print(f"\nDone. Success: {success}, Failed: {failed}, Total: {len(codes)}")


def download_sample() -> None:
    """下载5只样本股用于验证。

    000001 平安银行, 600000 浦发银行, 000858 五粮液,
    600519 贵州茅台, 002594 比亚迪
    """
    sample = ["000001", "600000", "000858", "600519", "002594"]
    names = {
        "000001": "平安银行",
        "600000": "浦发银行",
        "000858": "五粮液",
        "600519": "贵州茅台",
        "002594": "比亚迪",
    }
    print(f"Downloading {len(sample)} sample stocks...")

    for i, code in enumerate(sample, 1):
        try:
            df = fetch_stock_daily(code, "20150101", "20241231")
            path = save_stock_daily(df, code)
            print(
                f"[{i}/{len(sample)}] {names.get(code, code)} "
                f"({code}): {len(df)} rows -> {path}"
            )
        except Exception as exc:
            print(f"[{i}/{len(sample)}] FAILED {code}: {exc}")
        time.sleep(0.3)

    print("Sample download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download A-share stock data")
    parser.add_argument("--sample", action="store_true", help="下载5只样本股")
    parser.add_argument("--all", action="store_true", help="下载全部A股")
    parser.add_argument("--start", default="20150101", help="起始日期 YYYYMMDD")
    parser.add_argument("--end", default="20241231", help="结束日期 YYYYMMDD")
    parser.add_argument("--max", type=int, default=None, help="最大下载数量")
    args = parser.parse_args()

    if args.sample:
        download_sample()
    elif args.all:
        download_all(args.start, args.end, args.max)
    else:
        parser.print_help()
