from fastapi import BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select

from app.core.auth import check_access
from app.core.config import templates, ADMIN_EMAIL
from app.core.emailing import send_email
from app.models import SessionDep, get_user_devices
from app.models.command_request import CommandRequest

from . import cmdRequestApi


def _send_user_confirmation(to, user_email, user_id, name, description, status, submitted_at):
    body = templates.get_template("email/cmdRequestConfirmation.html").render(
        cmd_name=name,
        cmd_description=description,
        cmd_status=status,
        submitted_at=submitted_at,
        user_email=user_email,
        user_id=user_id,
    )
    send_email(
        to=to,
        subject=f"N.I.X — Command Request Received: /{name}",
        body=body,
    )


def _send_admin_notification(admin_to, user_email, user_id, name, description, status, submitted_at, devices):
    body = templates.get_template("email/cmdRequestAdminNotification.html").render(
        user_email=user_email,
        user_id=user_id,
        cmd_name=name,
        cmd_description=description,
        cmd_status=status,
        submitted_at=submitted_at,
        devices=devices,
    )
    send_email(
        to=admin_to,
        subject=f"N.I.X — New Command Request from {user_email}",
        body=body,
    )


@cmdRequestApi.post("/cmd-requests")
async def create_cmd_request(
    data: dict,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    user=Depends(check_access),
):
    if user is None:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    if not name:
        return JSONResponse({"success": False, "message": "Name is required"}, status_code=400)
    if not description:
        return JSONResponse({"success": False, "message": "Description is required"}, status_code=400)

    request = CommandRequest(
        user_id=user.uid,
        name=name,
        description=description,
    )
    try:
        session.add(request)
        session.commit()
        session.refresh(request)
    except Exception as e:
        session.rollback()
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

    # Gather devices for notification (before session closes)
    user_devices = get_user_devices(user.uid, session)
    devices_data = [
        {"name": d.name, "type": d.type, "ip": d.ip, "is_active": d.is_active}
        for d in (user_devices or [])
    ]

    submitted_at = request.created_at.isoformat()

    # Send emails in background (after response, session closed)
    background_tasks.add_task(
        _send_user_confirmation,
        to=user.notification_email or user.email,
        user_email=user.email,
        user_id=user.uid,
        name=name,
        description=description,
        status="pending",
        submitted_at=submitted_at,
    )
    background_tasks.add_task(
        _send_admin_notification,
        admin_to=ADMIN_EMAIL,
        user_email=user.email,
        user_id=user.uid,
        name=name,
        description=description,
        status="pending",
        submitted_at=submitted_at,
        devices=devices_data,
    )

    return JSONResponse({
        "success": True,
        "message": "Command request submitted",
        "data": {"id": request.id, "name": request.name, "status": request.status},
    }, status_code=201)


@cmdRequestApi.get("/cmd-requests")
async def list_cmd_requests(
    session: SessionDep,
    user=Depends(check_access),
):
    if user is None:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    try:
        statement = select(CommandRequest).where(
            CommandRequest.user_id == user.uid
        ).order_by(CommandRequest.created_at.desc())
        results = session.exec(statement).all()
        return JSONResponse({
            "success": True,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in results
            ],
        }, status_code=200)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
