from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_conversation_experience_cases import (  # noqa: E402
    add_group_scenario_card,
    case_to_dict,
    disable_case,
    import_cases_from_jsonl,
    import_seed_owner_cases,
    initialize_conversation_experience_cases,
    list_cases,
    update_case_review_status,
    upsert_case,
)
from xinyu_conversation_experience_matcher import match_conversation_experience_cases  # noqa: E402
from xinyu_conversation_experience_sidecar import render_conversation_experience_prompt_block  # noqa: E402
from xinyu_public_dataset_case_importer import import_public_dataset_cases  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage XinYu conversation experience cases.")
    parser.add_argument("--root", default=str(ROOT), help="XinYu app root.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    add = sub.add_parser("add")
    add.add_argument("--json", required=True, help="Path to a case JSON file.")
    add.add_argument("--group-card", action="store_true", help="Import as pending reviewed-group scenario card.")

    imp = sub.add_parser("import")
    imp.add_argument("--jsonl", required=True, help="Path to case JSONL.")
    imp.add_argument("--default-review-status", default="")

    public_imp = sub.add_parser("import-public")
    public_imp.add_argument("--dataset-id", required=True, help="Registry dataset id, such as lufy or lccc_base.")
    public_imp.add_argument(
        "--dataset",
        action="append",
        help="Local public dataset file, directory, or alias. Defaults to resolving --dataset-id from library/datasets.",
    )
    public_imp.add_argument("--limit", type=int, default=50)
    public_imp.add_argument("--dry-run", action="store_true")
    public_imp.add_argument("--include-backlog", action="store_true")
    public_imp.add_argument("--allow-blocked-after-owner-review", action="store_true")
    public_imp.add_argument("--allow-observation-only", action="store_true")

    sub.add_parser("seed")

    lst = sub.add_parser("list")
    lst.add_argument("--status", default="")
    lst.add_argument("--limit", type=int, default=20)

    approve = sub.add_parser("approve")
    approve.add_argument("case_id")
    approve.add_argument("--note", default="cli_approved")

    disable = sub.add_parser("disable")
    disable.add_argument("case_id")
    disable.add_argument("--reason", default="cli_disabled")

    match = sub.add_parser("match")
    match.add_argument("--text", required=True)
    match.add_argument("--owner", action="store_true")
    match.add_argument("--message-type", default="private_text")
    match.add_argument("--render", action="store_true")

    args = parser.parse_args()
    root = Path(args.root)

    if args.command == "init":
        print(json.dumps(initialize_conversation_experience_cases(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "add":
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
        case = add_group_scenario_card(root, data) if args.group_card else upsert_case(root, data)
        print(json.dumps(case_to_dict(case), ensure_ascii=False, indent=2))
        return 0
    if args.command == "import":
        print(
            json.dumps(
                import_cases_from_jsonl(
                    root,
                    Path(args.jsonl),
                    default_review_status=args.default_review_status or None,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "import-public":
        print(
            json.dumps(
                import_public_dataset_cases(
                    root,
                    [Path(item) for item in args.dataset or ()],
                    dataset_id=args.dataset_id,
                    limit=args.limit,
                    write=not args.dry_run,
                    include_backlog=args.include_backlog,
                    allow_blocked_after_owner_review=args.allow_blocked_after_owner_review,
                    allow_observation_only=args.allow_observation_only,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "seed":
        print(json.dumps(import_seed_owner_cases(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "list":
        cases = list_cases(root, review_status=args.status or None, limit=args.limit)
        print(json.dumps([case_to_dict(case) for case in cases], ensure_ascii=False, indent=2))
        return 0
    if args.command == "approve":
        ok = update_case_review_status(root, args.case_id, review_status="approved", note=args.note)
        print(json.dumps({"updated": ok}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if args.command == "disable":
        ok = disable_case(root, args.case_id, reason=args.reason)
        print(json.dumps({"updated": ok}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if args.command == "match":
        payload = {"message_type": args.message_type, "metadata": {"is_owner_user": bool(args.owner)}}
        result = match_conversation_experience_cases(root, payload, user_text=args.text)
        if args.render:
            print(render_conversation_experience_prompt_block(result))
        else:
            print(
                json.dumps(
                    {
                        "selected": [
                            {"case_id": decision.case.case_id, "score": round(decision.score, 4)}
                            for decision in result.selected
                        ],
                        "suppressed": [
                            {"case_id": decision.case.case_id, "reason": decision.reason}
                            for decision in result.suppressed[:10]
                        ],
                        "notes": list(result.notes),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
