import asyncio
import decimal
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import asyncpg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

app = FastAPI()

QUERIES_DIR = Path("/mnt/ssd_238/demo_queries")

BENCHMARK_DB = {
    "TPC-DS VAQ": "tpcds",
    "TPC-H VAQ":  "wns41559",
}
DEFAULT_DB = "wns41559"

def get_dsn(benchmark: str, port: int) -> dict:
    db = BENCHMARK_DB.get(benchmark, DEFAULT_DB)
    return {"host": "/tmp", "port": port, "user": "wns41559", "database": db}

EXQUTOR_PORT = 55432
VANILLA_PORT  = 55433
DIST_CONFIG = {
    "TPC-H VAQ": {"min": 0.80, "max": 1.00, "default": 0.875},
    "TPC-DS VAQ": {"min": 0.95, "max": 1.35, "default": 1.08},
}
DIST_FALLBACK = {"min": 0.80, "max": 1.35, "default": 1.00}


# ── Discovery ──────────────────────────────────────────────────────────────────

def get_benchmarks() -> dict[str, list[str]]:
    """Return {benchmark_name: [query_name, ...]} by scanning demo_queries/."""
    result = {}
    for bench_dir in sorted(QUERIES_DIR.iterdir()):
        if not bench_dir.is_dir():
            continue
        queries = sorted(f.stem for f in bench_dir.glob("*.sql"))
        if queries:
            result[bench_dir.name] = queries
    return result


def get_prefix_paths(benchmark: str, prefer_sampling: bool = False) -> list[Path]:
    """Return candidate prefix file paths in lookup order."""
    benchmark_dir = QUERIES_DIR / benchmark
    if prefer_sampling:
        return [
            benchmark_dir / "sampling_prefix.sql",
            QUERIES_DIR / "sampling_prefix.sql",
            benchmark_dir / "prefix.sql",
            QUERIES_DIR / "prefix.sql",
        ]
    return [benchmark_dir / "prefix.sql", QUERIES_DIR / "prefix.sql"]


def get_prefix_stmts(benchmark: str, prefer_sampling: bool = False) -> list[str]:
    """Load prefix SQL statements with optional sampling-prefix preference."""
    for path in get_prefix_paths(benchmark, prefer_sampling):
        if path.exists():
            content = path.read_text()
            variables = parse_psql_variables(content)
            return parse_prefix(content, variables)
    return []


def get_prefix_variables(benchmark: str, prefer_sampling: bool = False) -> dict[str, str]:
    """Load \\set variables from prefix SQL with optional sampling preference."""
    for path in get_prefix_paths(benchmark, prefer_sampling):
        if path.exists():
            return parse_psql_variables(path.read_text())
    return {}


def parse_psql_variables(content: str) -> dict[str, str]:
    """Collect psql-style \\set variables from SQL text."""
    variables: dict[str, str] = {}
    for m in re.finditer(r"\\set\s+(\w+)\s+'(.+?)'", content, re.DOTALL):
        variables[m.group(1)] = m.group(2)
    return variables


def apply_psql_variables(sql: str, variables: dict[str, str]) -> str:
    """Apply psql variable references (:'VAR', :VAR) to SQL text."""
    for var, val in variables.items():
        esc = re.escape(var)
        sql = re.sub(rf":'{esc}'", f"'{val}'", sql)
        sql = re.sub(rf":{esc}\b", val, sql)
    return sql


def get_dist_config(benchmark: str | None) -> dict[str, float]:
    return DIST_CONFIG.get(benchmark or "", DIST_FALLBACK)


def normalize_distance(distance: float | None, benchmark: str | None = None) -> float:
    """Clamp + round distance threshold using benchmark-specific bounds."""
    cfg = get_dist_config(benchmark)
    value = cfg["default"] if distance is None else float(distance)
    return round(max(cfg["min"], min(cfg["max"], value)), 3)


def apply_distance_threshold(sql: str, distance_threshold: float | None,
                             benchmark: str | None = None) -> str:
    """Replace vector distance predicate threshold when present."""
    if distance_threshold is None:
        return sql
    threshold = normalize_distance(distance_threshold, benchmark)
    threshold_str = f"{threshold:.3f}".rstrip("0").rstrip(".")
    return re.sub(
        r"(<->\s*:'\w+'::vector\(\d+\)\s*<\s*)([-+]?\d*\.?\d+)",
        rf"\g<1>{threshold_str}",
        sql,
        flags=re.IGNORECASE,
    )


def parse_prefix(content: str, variables: dict[str, str] | None = None) -> list[str]:
    """Parse prefix.sql and return executable SQL stmts."""
    variables = variables or parse_psql_variables(content)
    sql_lines = [l for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("\\")]
    sql = "\n".join(sql_lines)
    sql = apply_psql_variables(sql, variables)

    return [s.strip() for s in sql.split(";") if s.strip()]


# ── SQL parsing ────────────────────────────────────────────────────────────────

def parse_sql_file(benchmark: str, query_name: str,
                   inherited_variables: dict[str, str] | None = None,
                   distance_threshold: float | None = None):
    """Return (display_sql, select_stmt, explain_stmt)."""
    content = (QUERIES_DIR / benchmark / f"{query_name}.sql").read_text()

    variables: dict[str, str] = dict(inherited_variables or {})
    variables.update(parse_psql_variables(content))

    sql_lines = [l for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("\\")]
    sql = "\n".join(sql_lines)

    sql = apply_distance_threshold(sql, distance_threshold, benchmark)
    sql = apply_psql_variables(sql, variables)

    # Strip setup lines already handled by prefix
    lines = []
    for line in sql.splitlines():
        s = line.strip().upper()
        if s.startswith("LOAD ") or s.startswith("SET "):
            continue
        lines.append(line)
    query_sql = "\n".join(lines).strip().rstrip(";")

    select_stmt = re.sub(
        r"(?is)^\s*EXPLAIN\s*(?:\([^)]*\))?\s*(?:ANALYZE\s+)?",
        "",
        query_sql,
    ).strip()
    explain_stmt = (
        "EXPLAIN (ANALYZE, VERBOSE, BUFFERS, FORMAT JSON) "
        f"{select_stmt}"
    )

    # Display: shorten vector literals
    display = select_stmt
    for var, val in variables.items():
        if len(val) > 60:
            display = display.replace(f"'{val}'", f"'[{val[:40]}...]'")

    return display, select_stmt, explain_stmt


def strip_block_comments(sql: str) -> str:
    """Remove SQL block comments (/* ... */) and trim trailing spaces."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"[ \t]+\n", "\n", sql)
    return sql.strip()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def serialize_value(v):
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


async def run_select(dsn: dict, prefix_stmts: list[str],
                     select_stmt: str, use_index: bool = True) -> dict:
    conn = await asyncpg.connect(**dsn)
    try:
        for stmt in prefix_stmts:
            await conn.execute(stmt)
        if not use_index:
            await conn.execute("SET pg_hint_plan.enable_hint = off")
            select_stmt = strip_block_comments(select_stmt)

        t0 = time.perf_counter()
        rows = await conn.fetch(select_stmt)
        exec_time = (time.perf_counter() - t0) * 1000

        columns = list(rows[0].keys()) if rows else []
        data = [[serialize_value(row[c]) for c in columns] for row in rows]

        print(f"[select] port={dsn['port']} rows={len(rows)} time={exec_time:.1f}ms")
        return {"success": True, "columns": columns, "rows": data, "exec_time": exec_time}
    except Exception as e:
        print(f"[select] port={dsn['port']} ERROR: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await conn.close()


async def run_explain(dsn: dict, prefix_stmts: list[str],
                      explain_stmt: str, use_index: bool = True) -> dict:
    conn = await asyncpg.connect(**dsn)
    try:
        for stmt in prefix_stmts:
            await conn.execute(stmt)
        if not use_index:
            await conn.execute("SET pg_hint_plan.enable_hint = off")
            explain_stmt = strip_block_comments(explain_stmt)

        plan_json = await conn.fetchval(explain_stmt)
        if isinstance(plan_json, str):
            plan_json = json.loads(plan_json)

        # EXPLAIN FORMAT JSON returns a one-element array by default.
        root = plan_json[0] if isinstance(plan_json, list) and plan_json else {}
        exec_time = root.get("Execution Time")
        plan_time = root.get("Planning Time")

        return {
            "success": True,
            "plan_json": plan_json,
            "exec_time": exec_time,
            "plan_time": plan_time,
        }
    except Exception as e:
        print(f"[explain] port={dsn['port']} ERROR: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await conn.close()


# ── API ────────────────────────────────────────────────────────────────────────

@app.get("/queries")
async def list_queries():
    return get_benchmarks()


@app.get("/sql/{benchmark}/{query_name}")
async def get_sql(benchmark: str, query_name: str, distance: float | None = None):
    benchmark = unquote(benchmark)
    try:
        dist = normalize_distance(distance, benchmark)
        prefix_vars = get_prefix_variables(benchmark)
        display, _, _ = parse_sql_file(benchmark, query_name, prefix_vars, dist)
        return {"sql": display}
    except Exception as e:
        return {"error": str(e)}


@app.get("/run/{benchmark}/{query_name}")
async def run(benchmark: str, query_name: str, use_index: str = "yes",
              distance: float | None = None):
    benchmark = unquote(benchmark)
    dist = normalize_distance(distance, benchmark)
    idx = use_index.lower() != "no"
    prefer_sampling = not idx
    prefix_stmts = get_prefix_stmts(benchmark, prefer_sampling)
    prefix_vars = get_prefix_variables(benchmark, prefer_sampling)
    _, select_stmt, _ = parse_sql_file(benchmark, query_name, prefix_vars, dist)

    async def event_stream():
        yield f"data: {json.dumps({'event': 'start'})}\n\n"

        exqutor_task = asyncio.create_task(
            run_select(get_dsn(benchmark, EXQUTOR_PORT), prefix_stmts, select_stmt, idx))
        vanilla_task = asyncio.create_task(
            run_select(get_dsn(benchmark, VANILLA_PORT),  prefix_stmts, select_stmt, idx))
        task_names = {exqutor_task: "exqutor", vanilla_task: "vanilla"}

        pending = set(task_names)
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                result["source"] = task_names[task]
                yield f"data: {json.dumps(result)}\n\n"

        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/plan/{benchmark}/{query_name}")
async def get_plan(benchmark: str, query_name: str, source: str = "exqutor",
                   use_index: str = "yes", distance: float | None = None):
    benchmark = unquote(benchmark)
    dist = normalize_distance(distance, benchmark)
    idx = use_index.lower() != "no"
    prefer_sampling = not idx
    port = EXQUTOR_PORT if source == "exqutor" else VANILLA_PORT
    dsn = get_dsn(benchmark, port)
    prefix_stmts = get_prefix_stmts(benchmark, prefer_sampling)
    prefix_vars = get_prefix_variables(benchmark, prefer_sampling)
    _, _, explain_stmt = parse_sql_file(benchmark, query_name, prefix_vars, dist)
    result = await run_explain(dsn, prefix_stmts, explain_stmt, idx)
    return JSONResponse(result)


@app.get("/")
async def root():
    return HTMLResponse((Path(__file__).parent / "index.html").read_text())
