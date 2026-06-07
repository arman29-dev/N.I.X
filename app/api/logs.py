import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import Depends, Query
from fastapi.responses import JSONResponse

from app.core.auth import check_access
from app.core.config import LOG_DIR

from . import logApi


LOG_FILES = {
    "server": "server.log",
    "security": "security.log",
    "errors": "errors.log",
}

_LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+\|\s+(\w+)\s+\|\s+(.+)$"
)


@logApi.get("/logs/{log_type}")
async def get_logs(
    log_type: str,
    lines: int = Query(50, ge=1, le=5000),
    user=Depends(check_access),
):
    if user is None:
        return JSONResponse({"msg": "Unauthorized"}, status_code=401)

    if log_type not in LOG_FILES:
        return JSONResponse(
            {"msg": f"Invalid log type. Choose from: {', '.join(LOG_FILES)}"},
            status_code=400,
        )

    log_path = Path(LOG_DIR) / LOG_FILES[log_type]
    if not log_path.exists():
        return JSONResponse({"data": []}, status_code=200)

    try:
        with open(log_path, "r") as f:
            # Efficient tail: seek to end and read backwards
            f.seek(0, os.SEEK_END)
            size = f.tell()

            buffer = []
            chunk_size = 4096
            pos = size
            while pos > 0 and len(buffer) < lines:
                read_size = min(chunk_size, pos)
                pos -= read_size
                f.seek(pos)
                chunk = f.read(read_size)
                buffer.append(chunk)

            content = "".join(reversed(buffer))
            raw_lines = content.rstrip("\n").split("\n")
            raw_lines = raw_lines[-lines:]

            entries = []
            for line in raw_lines:
                m = _LOG_LINE_RE.match(line)
                if m:
                    entries.append({
                        "timestamp": m.group(1),
                        "level": m.group(2),
                        "message": m.group(3),
                    })
                else:
                    entries.append({
                        "timestamp": None,
                        "level": None,
                        "message": line,
                    })

            return JSONResponse({"data": entries}, status_code=200)

    except Exception as e:
        return JSONResponse({"msg": str(e)}, status_code=500)
