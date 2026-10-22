from __future__ import annotations

import argparse
import csv
from pathlib import Path

from numbers_parser import Document

from app.db import init_db
from app.services import cadre_login, import_villager_roster


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import villager roster from a .numbers file")
    parser.add_argument("--numbers-file", required=True, help="Path to .numbers file")
    parser.add_argument(
        "--output-csv",
        default="data/deshengcun_roster_from_numbers.csv",
        help="Intermediate CSV output path",
    )
    parser.add_argument("--manager-name", default="示例人员1")
    parser.add_argument("--manager-password", default="999999")
    return parser.parse_args()


def convert_numbers_to_csv(numbers_file: Path, output_csv: Path) -> int:
    doc = Document(str(numbers_file))
    table = doc.sheets[0].tables[0]
    rows: list[dict[str, str]] = []
    for idx in range(1, table.num_rows):
        group_name = str(table.cell(idx, 1).value or "").strip()
        full_name = str(table.cell(idx, 2).value or "").strip()
        id_card = str(table.cell(idx, 5).value or "").strip()
        if not full_name or not id_card:
            continue
        rows.append(
            {
                "姓名": full_name,
                "身份证号": id_card,
                "组别": group_name,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=["姓名", "身份证号", "组别"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    args = parse_args()
    numbers_file = Path(args.numbers_file).expanduser().resolve()
    output_csv = Path(args.output_csv).resolve()

    if not numbers_file.exists():
        raise SystemExit(f"numbers file not found: {numbers_file}")

    row_count = convert_numbers_to_csv(numbers_file, output_csv)
    init_db()
    login = cadre_login(
        {
            "manager_name": args.manager_name,
            "manager_password": args.manager_password,
        }
    )
    result = import_villager_roster(login["token"], output_csv.name, output_csv.read_bytes())

    print(f"converted rows: {row_count}")
    print(f"csv: {output_csv}")
    print(f"import result: {result}")


if __name__ == "__main__":
    main()
