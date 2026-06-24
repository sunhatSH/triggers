"""triggerctl command-line interface."""
from __future__ import annotations

import argparse
import sys

from . import commands, poll as poll_mod
from .roots import resolve


def _add_root_arg(p):
    p.add_argument("--root", default=None,
                   help="user | project | all | <path>（默认：写命令=user，读命令=all）")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="triggerctl",
        description="Triggers for Claude Code, Hermes Agent, and Codex CLI",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化一个注册根")
    _add_root_arg(p)

    p = sub.add_parser("add", help="注册新触发器，或 --from 从 Git/本地安装")
    p.add_argument("name", nargs="?", help="触发器名称（--from 时可省略）")
    _add_root_arg(p)
    p.add_argument("--from", dest="source", metavar="SOURCE",
                   help="从 GitHub(owner/repo[/path])、git URL 或本地路径安装")
    p.add_argument("--list", dest="list_only", action="store_true",
                   help="配合 --from：只列出 SOURCE 中的触发器，不安装")
    p.add_argument("--category", help="子目录分组（生成 <category>-triggers/）")
    p.add_argument("--every", choices=["day", "hour", "week", "month"], help="定时：周期")
    p.add_argument("--at", help='定时：时刻 "HH:MM" 或 ":MM"')
    p.add_argument("--on", help="定时：week 的星期 / month 的日号")
    p.add_argument("--dedup", help="定时去重粒度（默认同 every）")
    p.add_argument("--probe", help="条件：返回 0 即成立的 shell 命令（轮询评估）")
    p.add_argument("--dedup-cmd", dest="dedup_cmd", help="条件：事件实例键命令")
    p.add_argument("--when", help="会话内语义条件：由 Agent 自己判断的自然语言条件（轮询不评估）")
    p.add_argument("--locked", action="store_true", help="不可关闭：disable/remove 会被拒绝")
    p.add_argument("--disabled", action="store_true", help="创建为停用")
    p.add_argument("--force", action="store_true", help="覆盖同名文件")

    p = sub.add_parser("remove", help="删除触发器")
    p.add_argument("name")
    _add_root_arg(p)

    for verb, en in (("enable", True), ("disable", False)):
        p = sub.add_parser(verb, help=f"{verb} 触发器")
        p.add_argument("name")
        _add_root_arg(p)

    p = sub.add_parser("list", help="列出触发器")
    _add_root_arg(p)

    p = sub.add_parser("sync", help="由触发器文件重新生成 TRIGGERS.md 索引")
    _add_root_arg(p)

    p = sub.add_parser("status", help="查看 run-log")
    _add_root_arg(p)
    p.add_argument("-n", "--limit", type=int, default=20)

    p = sub.add_parser("detect", help="便宜检测层：判定哪些 DUE（不调模型）")
    _add_root_arg(p)

    p = sub.add_parser("poll", help="检测 + 仅对 DUE 调模型执行")
    _add_root_arg(p)
    p.add_argument("--dry-run", action="store_true", help="只检测不执行（等同 detect）")

    p = sub.add_parser("install", help="生成定时启动入口 / 安装会话注入 hook")
    _add_root_arg(p)
    p.add_argument("--cron", action="store_true", help="打印 crontab 行")
    p.add_argument("--loop", action="store_true", help="生成 while+sleep 循环脚本")
    p.add_argument("--hook", action="store_true", help="Claude Code UserPromptSubmit hook → settings.json")
    p.add_argument("--hermes-hook", action="store_true", help="Hermes pre_llm_call hook only")
    p.add_argument("--hermes", action="store_true", help="Full Hermes setup: hook + skill + hooks_auto_accept")
    p.add_argument("--codex-hook", action="store_true", help="Codex UserPromptSubmit hook only")
    p.add_argument("--codex", action="store_true", help="Full Codex setup: hook + skill")
    p.add_argument("--statusline", action="store_true", help="Claude Code statusLine (rest / too-many warnings)")
    p.add_argument("--interval", type=int, default=60, help="循环间隔秒（默认 60）")

    p = sub.add_parser("uninstall", help="Remove hooks/skills and trigger registry data")
    _add_root_arg(p)
    p.add_argument(
        "--agent",
        choices=("claude", "hermes", "codex", "all"),
        default="all",
        help="Which agent integration to remove (default: all)",
    )
    p.add_argument("--yes", "-y", action="store_true", help="Confirm destructive trigger deletion")
    p.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    p.add_argument(
        "--keep-triggers",
        action="store_true",
        help="Remove hooks/skills only; keep user/project/system trigger files",
    )
    p.add_argument(
        "--triggers-only",
        action="store_true",
        help="Remove trigger data only; keep agent hooks and skills",
    )

    sub.add_parser("hook", help="Session trigger block (Claude Code UserPromptSubmit)")
    sub.add_parser("hermes-hook", help="Session trigger JSON (Hermes pre_llm_call)")
    sub.add_parser("codex-hook", help="Session trigger JSON (Codex UserPromptSubmit)")
    sub.add_parser("statusline", help="Status line text (Claude Code statusLine)")

    sub.add_parser("doctor", help="检查安装、hook、索引、轮询等是否正常")

    p = sub.add_parser("update", help="按 triggers-lock.json 更新已安装的远程触发器")
    _add_root_arg(p)
    p.add_argument("--force", action="store_true", help="覆盖本地已改动的同名触发器")

    p = sub.add_parser("validate", help="校验触发器 frontmatter、重名、索引是否过期")
    _add_root_arg(p)
    p.add_argument("--probe-test", action="store_true", help="试跑 probe/dedup_cmd（应只读）")

    return ap


def _cmd_detect(selector) -> int:
    roots = resolve(selector)
    rep = poll_mod.poll(roots, do_execute=False)
    if not rep.outcomes:
        print("（没有触发器）")
        return 0
    for o in rep.outcomes:
        flag = "DUE " if o.status == "due" else "    "
        print(f"{flag}[{o.status}] {o.name}  key={o.key}  {o.reason}")
    print(f"\n汇总: {rep.summary()}")
    return 0


def _cmd_poll(selector, dry_run) -> int:
    roots = resolve(selector)
    rep = poll_mod.poll(roots, do_execute=not dry_run)
    for o in rep.outcomes:
        if o.status in ("executed", "failed", "due"):
            print(f"[{o.status}] {o.name}  key={o.key}  {o.reason}")
            if o.output:
                print("  >", o.output.replace("\n", "\n  > "))
    print(f"\n[{rep.started_at}] 汇总: {rep.summary()}")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    c = args.cmd
    if c == "init":
        return commands.cmd_init(args.root)
    if c == "add":
        return commands.cmd_add(args.name, args.root, args.category, args.every, args.at,
                                args.on, args.dedup, args.probe, args.dedup_cmd,
                                args.when, args.disabled, args.force, args.locked,
                                args.source, args.list_only)
    if c == "doctor":
        return commands.cmd_doctor()
    if c == "update":
        return commands.cmd_update(args.root, args.force)
    if c == "validate":
        return commands.cmd_validate(args.root, args.probe_test)
    if c == "remove":
        return commands.cmd_remove(args.name, args.root)
    if c == "enable":
        return commands.cmd_toggle(args.name, args.root, True)
    if c == "disable":
        return commands.cmd_toggle(args.name, args.root, False)
    if c == "list":
        return commands.cmd_list(args.root)
    if c == "sync":
        return commands.cmd_sync(args.root)
    if c == "status":
        return commands.cmd_status(args.root, args.limit)
    if c == "detect":
        return _cmd_detect(args.root)
    if c == "poll":
        return _cmd_poll(args.root, args.dry_run)
    if c == "install":
        mode = (
            "hook" if args.hook
            else "hermes" if args.hermes
            else "codex" if args.codex
            else "hermes-hook" if args.hermes_hook
            else "codex-hook" if args.codex_hook
            else "statusline" if args.statusline
            else "cron" if args.cron
            else "loop"
        )
        return commands.cmd_install(args.root, mode, args.interval)
    if c == "uninstall":
        return commands.cmd_uninstall(
            args.root,
            agents=args.agent,
            yes=args.yes,
            dry_run=args.dry_run,
            keep_triggers=args.keep_triggers,
            triggers_only=args.triggers_only,
        )
    if c == "hook":
        return commands.cmd_hook()
    if c == "hermes-hook":
        return commands.cmd_hermes_hook()
    if c == "codex-hook":
        return commands.cmd_codex_hook()
    if c == "statusline":
        return commands.cmd_statusline()
    return 2


if __name__ == "__main__":
    sys.exit(main())
