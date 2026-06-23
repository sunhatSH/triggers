"""User-facing commands: init, add, remove, enable/disable, list, status, sync, install."""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import frontmatter, registry, runlog
from .model import Trigger, discover, find
from .roots import Root, primary, resolve

BODY_STUB = "# {name}\n\n触发后要执行的步骤（写给模型看的自然语言指令）：\n\n- TODO：在此填写动作步骤。\n"

# ---- 默认/系统级护栏触发器（locked，不可关闭） ----
WARN_NAME = "too-many-triggers-warning"
WARN_WHEN = "本索引「注册表」中启用(列出)的触发器数量超过 20 个时"
WARN_BODY = """# too-many-triggers-warning

提醒用户「启用的触发器过多，会占用每次请求的上下文」。这是系统级护栏，`locked: true` 不可关闭。

步骤：
1. 数一下索引「注册表」里启用(列出)的触发器条数 N（不含已停用的）。
2. 若 N > 20：提醒用户（消息开头标来源）——"[触发器: too-many-triggers-warning] 当前启用触发器 N 个，已超过 20，会持续占用上下文；建议 `triggerctl disable <名称>` 停用不常用的（停用即不占上下文）。"
3. N ≤ 20：不要提示，安静跳过。
"""


def _seed_defaults(root: Root) -> bool:
    """Create the locked guardrail trigger if absent. Returns True if created."""
    path = root.path / "system-triggers" / f"{WARN_NAME}.md"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write_file(
        path,
        {"name": WARN_NAME, "enabled": True, "locked": True, "when": WARN_WHEN},
        WARN_BODY,
    )
    return True


# ---------- helpers ----------

def _print_table(rows: List[List[str]], headers: List[str]) -> None:
    cols = list(zip(*([headers] + rows))) if rows else [[h] for h in headers]
    widths = [max(len(str(c)) for c in col) for col in cols]
    def fmt(r):
        return "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))


def _sync_roots(roots: List[Root]) -> None:
    for r in roots:
        if r.path.is_dir():
            registry.sync(r)


# ---------- commands ----------

def cmd_init(selector: Optional[str]) -> int:
    root = primary(selector)
    root.path.mkdir(parents=True, exist_ok=True)
    root.state_dir.mkdir(parents=True, exist_ok=True)
    (root.state_dir / "run-log.jsonl").touch(exist_ok=True)
    if _seed_defaults(root):
        print(f"已植入默认护栏触发器：{WARN_NAME}（locked）")
    n = registry.sync(root)
    print(f"已初始化 {root}  (索引 {n} 个触发器)")
    print(f"索引: {root.index_file}")
    return 0


def cmd_add(
    name: str,
    selector: Optional[str],
    category: Optional[str],
    every: Optional[str],
    at: Optional[str],
    on: Optional[str],
    dedup: Optional[str],
    probe: Optional[str],
    dedup_cmd: Optional[str],
    when: Optional[str],
    disabled: bool,
    force: bool,
    locked: bool = False,
) -> int:
    if not every and not probe and not when:
        print("错误：至少要 --every（定时）、--probe（条件）或 --when（会话内语义条件）其一", file=sys.stderr)
        return 2
    root = primary(selector)
    folder = root.path / (f"{category}-triggers" if category else "")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    if path.exists() and not force:
        print(f"错误：{path} 已存在（--force 覆盖）", file=sys.stderr)
        return 2

    meta = {"name": name, "enabled": not disabled}
    if locked:
        meta["locked"] = True
    if when:
        meta["when"] = when
    if every:
        sch = {"every": every}
        if at:
            sch["at"] = at
        if on is not None:
            sch["on"] = on
        meta["schedule"] = sch
        if dedup:
            meta["dedup"] = dedup
    if probe:
        meta["probe"] = probe
        if dedup_cmd:
            meta["dedup_cmd"] = dedup_cmd

    frontmatter.write_file(path, meta, BODY_STUB.format(name=name))
    registry.sync(root)
    print(f"已注册触发器 {name} -> {path}")
    print(f"  类型: {_kind(meta)}   编辑正文后即可生效")
    return 0


def _kind(meta: dict) -> str:
    if meta.get("when"):
        return "session"
    s, p = bool(meta.get("schedule")), bool(meta.get("probe"))
    return "time+event" if s and p else "time" if s else "event" if p else "invalid"


def cmd_remove(name: str, selector: Optional[str]) -> int:
    roots = resolve(selector)
    t = find(roots, name)
    if not t:
        print(f"未找到触发器 {name}", file=sys.stderr)
        return 1
    if t.locked:
        print(f"{name} 是 locked（不可关闭/删除）。如确需删除，先编辑其文件去掉 `locked: true` 再 remove。",
              file=sys.stderr)
        return 2
    t.path.unlink()
    registry.sync(t.root)
    print(f"已删除 {name} ({t.path})")
    return 0


def _set_enabled_text(path: Path, value: bool) -> None:
    text = path.read_text(encoding="utf-8")
    val = "true" if value else "false"
    lines = text.splitlines()
    # operate only inside the frontmatter block
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end:
            for i in range(1, end):
                if re.match(r"\s*enabled\s*:", lines[i]):
                    lines[i] = f"enabled: {val}"
                    break
            else:
                lines.insert(1, f"enabled: {val}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise ValueError("文件没有 frontmatter，无法切换 enabled")


def cmd_toggle(name: str, selector: Optional[str], enable: bool) -> int:
    roots = resolve(selector)
    t = find(roots, name)
    if not t:
        print(f"未找到触发器 {name}", file=sys.stderr)
        return 1
    if not enable and t.locked:
        print(f"{name} 是不可关闭（locked）的护栏触发器，拒绝停用。", file=sys.stderr)
        return 2
    _set_enabled_text(t.path, enable)
    registry.sync(t.root)
    print(f"{name} -> enabled={enable}")
    return 0


def cmd_list(selector: Optional[str]) -> int:
    roots = resolve(selector)
    rows = []
    for root in roots:
        for t in discover(root):
            en = ("on" if t.enabled else "off") + (" 🔒" if t.locked else "")
            rows.append([t.name, t.kind, en,
                         t.condition_summary(), f"{root.kind}:{t.rel_path}"])
    if not rows:
        print("（没有触发器）")
        return 0
    _print_table(rows, ["名称", "类型", "启用", "条件", "位置"])
    print("\n🔒 = 不可关闭（locked）")
    return 0


def cmd_sync(selector: Optional[str]) -> int:
    roots = resolve(selector)
    if not roots:
        print("没有可同步的注册根")
        return 0
    for root in roots:
        n = registry.sync(root)
        print(f"已生成 {root.index_file} ({n} 个触发器)")
    return 0


def cmd_status(selector: Optional[str], limit: int) -> int:
    roots = resolve(selector)
    for root in roots:
        entries = runlog.load(root)
        print(f"== {root}  (run-log {len(entries)} 条) ==")
        for e in entries[-limit:]:
            print(f"  {e.get('ran_at','?')}  {e.get('name','?')}  key={e.get('key','')}  {e.get('result','')}")
        if not entries:
            print("  (空)")
    return 0


def cmd_hook() -> int:
    """Print the session-trigger context block (used by the UserPromptSubmit hook)."""
    from . import hookgen
    block = hookgen.session_context()
    if block:
        print(block)
    return 0


def _triggerctl_cmd() -> str:
    """A robust way to invoke triggerctl from a hook (PATH may be minimal)."""
    import shutil
    return shutil.which("triggerctl") or f"{sys.executable} -m triggerctl"


def cmd_install_hook() -> int:
    """Merge a UserPromptSubmit hook into ~/.claude/settings.json so session triggers
    are injected into every prompt's context."""
    import json
    from pathlib import Path
    settings = Path.home() / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"读取 {settings} 失败: {e}", file=sys.stderr)
            return 1
        # back up before touching
        bak = settings.with_suffix(".json.triggerctl.bak")
        bak.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = f"{_triggerctl_cmd()} hook"
    hooks = data.setdefault("hooks", {})
    ups = hooks.setdefault("UserPromptSubmit", [])
    # idempotent: skip if our hook is already there
    for group in ups:
        for h in group.get("hooks", []):
            if "triggerctl hook" in h.get("command", "") or h.get("command") == cmd:
                print("UserPromptSubmit hook 已存在，跳过。")
                return 0
    ups.append({"hooks": [{"type": "command", "command": cmd}]})
    settings.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 UserPromptSubmit hook 到 {settings}")
    print(f"  命令: {cmd}")
    print("注意：仅对**新启动**的会话生效。")
    return 0


def cmd_install(selector: Optional[str], mode: str, interval: int) -> int:
    if mode == "hook":
        return cmd_install_hook()
    root = primary(selector)
    root.path.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    rootsel = root.kind
    if mode == "cron":
        # cron 用分钟级；间隔换算成 cron 不精确，这里给每分钟跑（poll 内部便宜）
        line = f"* * * * * {py} -m triggerctl poll --root {rootsel} >> {root.state_dir}/poll.out 2>&1"
        print("把下面这行加入 crontab（crontab -e）：\n")
        print("  " + line)
        return 0
    # loop launcher script
    script = root.path / "run-loop.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "# 由 `triggerctl install --loop` 生成。便宜检测每 N 秒一次，仅 DUE 时调模型。\n"
        "set -euo pipefail\n"
        f'INTERVAL="${{1:-{interval}}}"\n'
        f'export PATH="{Path(py).parent}:$PATH"\n'
        f'mkdir -p "{root.state_dir}"\n'
        "while true; do\n"
        f'  {py} -m triggerctl poll --root {rootsel} >> "{root.state_dir}/poll.out" 2>&1 || true\n'
        '  sleep "$INTERVAL"\n'
        "done\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    print(f"已生成循环启动脚本：{script}")
    print(f"后台启动：\n  nohup {script} {interval} >/dev/null 2>&1 &")
    return 0
