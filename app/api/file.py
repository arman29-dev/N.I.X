import hmac
import hashlib

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import UPLOAD_DIR, SECRET_KEY
from app.core.auth import check_access
from app.models import SessionDep, FileUpload, register_file_upload, get_file_upload
from app.models.users import User
from app.api.comms import manager


fileApi = APIRouter(
    prefix="/api/v1/comms",
    tags=["File Transfer API"],
)


def _encrypt_key(file_id: str) -> str:
    """Derive AES-256 key from SECRET_KEY + file_id (HMAC-SHA256)."""
    return hmac.new(
        SECRET_KEY.encode(), file_id.encode(), hashlib.sha256
    ).hexdigest()


def _xor_encrypt(data: bytes, key: str) -> bytes:
    """Simple XOR-based obfuscation using derived key (prevents plaintext-on-disk).
    For production, replace with AES-GCM. This uses a repeating-key XOR with the
    HMAC-derived hex key."""
    key_bytes = key.encode()
    return bytes(data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data)))


@fileApi.post("/upload")
async def upload_file(
    session: SessionDep,
    file: UploadFile = File(...),
    target_device: str = Form(default=None),
    current_user: User = Depends(check_access),
):
    user_id = current_user.uid

    # Validate file size (512MB max)
    contents = await file.read()
    if len(contents) > 512 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 512MB)")

    file_id = str(__import__("uuid").uuid4())
    safe_name = file.filename or "unnamed"
    # Sanitize filename
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ").strip()
    if not safe_name:
        safe_name = "unnamed"

    user_dir = UPLOAD_DIR / user_id / file_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / safe_name

    # Encrypt at rest
    key = _encrypt_key(file_id)
    encrypted = _xor_encrypt(contents, key)
    file_path.write_bytes(encrypted)

    mime = file.content_type or "application/octet-stream"

    upload = FileUpload(
        id=file_id,
        owner_uid=user_id,
        file_name=safe_name,
        file_size=len(contents),
        mime_type=mime,
        storage_path=str(file_path.relative_to(UPLOAD_DIR)),
    )

    status, msg = register_file_upload(upload, session)
    if status != 200:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=msg)

    # Send file_message to target device (or all devices if no target)
    event_data = {
        "file_id": file_id,
        "file_name": safe_name,
        "file_size": len(contents),
        "mime_type": mime,
        "from_device": "server",
    }
    if target_device and manager.is_device_connected(target_device):
        await manager.send_to_device(target_device, {
            "type": "event",
            "event": "file_message",
            "data": event_data,
        })
    else:
        await manager.send_to_user_device(user_id, {
            "type": "event",
            "event": "file_message",
            "data": event_data,
        })
    # Always send to browser dashboards so web clients see it
    await manager.send_to_user(user_id, {
        "type": "event",
        "event": "file_message",
        "data": event_data,
    })

    return JSONResponse({
        "success": True,
        "file_id": file_id,
        "file_name": safe_name,
        "file_size": len(contents),
    })


@fileApi.get("/download/{file_id}")
async def download_file(
    session: SessionDep,
    file_id: str,
    current_user: User = Depends(check_access),
):
    upload = get_file_upload(file_id, current_user.uid, session)
    if not upload:
        raise HTTPException(status_code=404, detail="File not found or expired")

    from datetime import datetime as dt
    if dt.now() > upload.expires_at:
        raise HTTPException(status_code=410, detail="File has expired")

    # Increment download counter
    upload.downloads += 1
    session.add(upload)
    session.commit()

    file_path = UPLOAD_DIR / upload.storage_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Decrypt
    key = _encrypt_key(file_id)
    encrypted = file_path.read_bytes()
    decrypted = _xor_encrypt(encrypted, key)

    # Write to temp file for FileResponse (or stream directly)
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload.file_name}")
    tmp.write(decrypted)
    tmp.close()

    return FileResponse(
        path=tmp.name,
        filename=upload.file_name,
        media_type=upload.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{upload.file_name}"',
            "Content-Length": str(upload.file_size),
        },
    )
