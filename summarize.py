import argparse
import json
import code
from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict
import typing
import statistics
import pandas as pd


@dataclass
class Summary:
    path: Path
    task: str
    status: str
    duration: float
    tokens: int
    steps: int
    model: str
    temperature: float
    files_read: set[str]
    files_written: set[str]
    tools_used: Counter[str]

    def print(self):
        print(f"{self.path}:")
        print(f"  {self.task} {self.status}")
        print(
            f"  took {self.duration:.0f} seconds, "
            + f"{self.tokens} tokens, "
            + f"{self.steps} steps"
        )
        print(f"  model: {self.model}, temperature: {self.temperature}")
        print(
            f"  tools used:    {', '.join(f'{t} {c} time{'s' if c != 1 else ''}' for t, c in self.tools_used.items())}"
        )
        print(f"  files read:    {', '.join(sorted(self.files_read))}")
        print(f"  files written: {', '.join(sorted(self.files_written))}")

    def tool_percentages(self) -> dict[str, float]:
        total = sum(self.tools_used.values())
        return {t: c / total for t, c in self.tools_used.items()}


def _function_calls(
    history: list[dict[str, dict]],
) -> typing.Generator[dict[str, dict], None, None]:
    for h in history:
        if not h:
            continue
        parts = h.get("parts")
        if parts:
            for p in parts:
                if p["function_call"]:
                    yield p["function_call"]


def summarize(path: Path) -> Summary:
    r = json.load(open(path, "rt"))

    status = "INCOMPLETE"
    if r["completed"]:
        status = "SUCCESS" if r["successful"] else "FAILURE"

    function_calls = list(_function_calls(r["history"]))

    tools_used = Counter([str(c["name"]) for c in function_calls])
    files_read = set()
    files_written = set()
    for c in function_calls:
        args = c["args"]
        if c["name"] == "read_file":
            files_read.add(args.get("path", ""))
        elif c["name"] == "read_files":
            files_read.update(args.get("paths", []))
        elif c["name"] == "write_file":
            files_written.add(args.get("path", ""))

    return Summary(
        path=path,
        task=r["task"],
        status=status,
        duration=r["duration"],
        tokens=r["usage"]["total_token_count"],
        steps=len(r["history"]),
        model=r["model"],
        temperature=r["temperature"],
        files_read=files_read,
        files_written=files_written,
        tools_used=tools_used,
    )


def min_mean_max(values: list) -> str:
    return f"{min(values):.2f} {statistics.mean(values):.2f} {max(values):.2f}"


def interactive(summaries: list[Summary]):
    code.interact(
        local={"pd": pd, "df": pd.DataFrame(summaries)},
        banner='Run summaries are in a Pandas DataFrame called "df"',
    )


def summarize_command(args: argparse.Namespace):
    # summaries run recordings
    summaries = [summarize(path) for path in args.recordings]

    if args.interactive:
        # open an interactive python shell with Pandas
        interactive(summaries)
        return

    if args.group_by:
        # show a grouped summary
        groups = list(sorted(set(getattr(s, args.group_by) for s in summaries)))
        for g in groups:
            group_summaries = [s for s in summaries if getattr(s, args.group_by) == g]
            print(f"{g}: {len(group_summaries)} runs")
            if args.group_by != "status":
                status_counts = Counter([s.status for s in group_summaries])
                for status, count in status_counts.items():
                    print(f"  {status}: {100*count/len(group_summaries):.1f}%")
            print(f"  duration: {min_mean_max([s.duration for s in group_summaries])}")
            print(f"  tokens: {min_mean_max([s.tokens for s in group_summaries])}")
            print(f"  steps: {min_mean_max([s.steps for s in group_summaries])}")
            tool_sums = defaultdict(float)
            for s in group_summaries:
                for t, p in s.tool_percentages().items():
                    tool_sums[t] += p
            tool_percentages = [
                (t, p * 100 / len(group_summaries)) for t, p in tool_sums.items()
            ]
            tool_percentages = sorted(
                tool_percentages, key=lambda x: x[1], reverse=True
            )
            print(f"  tools: {', '.join(f'{t} {p:.1f}%' for t, p in tool_percentages)}")
        return

    # just show summaries
    for s in summaries:
        s.print()
        print("")


def add_subcommand(subcommands: argparse._SubParsersAction):
    parser = subcommands.add_parser(
        "summarize", help="Summarize one or more task recordings."
    )
    parser.add_argument(
        "recordings", type=Path, nargs="+", help="The recordings to summarize."
    )
    mutex = parser.add_mutually_exclusive_group()

    mutex.add_argument("--group-by", choices=("status", "model", "temperature"))

    mutex.add_argument("--interactive", "-i", action="store_true")
