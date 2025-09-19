from fastapi import Request, Form
from fastapi.responses import JSONResponse

from app.core.auth import login_required

from app.models import SessionDep, get_user_access_token

from . import deviceApi, generate_device_qr

from uuid import uuid4
from typing import Annotated
from datetime import datetime, timedelta



@deviceApi.post("/generate-qr",)
@login_required()
async def show_device_qr(req: Request, device_type: Annotated[str, Form()], session: SessionDep, current_user_uid: str|None=None):
    if current_user_uid is None:
        return JSONResponse(
            {
                'success': False,
                'message': 'Unauthorized'
            }, status_code=401
        )

    if device_type == "smartphone":
        user_access_token = get_user_access_token(current_user_uid, session)
        device_uid = str(uuid4())
        qr_exp_time = datetime.now() + timedelta(days=30)

        status_code, stats, data = generate_device_qr(
            req=req, device_uid=device_uid, exp_time=qr_exp_time,
            owner_uid=current_user_uid, user_access_token=user_access_token,
        )

        return JSONResponse({
            'success': stats,
            'qr_path': data,
        }, status_code=status_code)
