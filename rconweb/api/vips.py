import datetime
import logging
import os
import re
from uuid import uuid4

from dateutil import parser
from django import forms
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from rcon.discord import send_to_discord_audit
from rcon.types import GameEnum
from rcon.utils import INDEFINITE_VIP_DATE
from rcon.vip_import import inventory
from rcon.workers import get_job_results, worker_bulk_vip

from .audit_log import record_audit
from .auth import api_response, login_required
from .decorators import permission_required, require_content_type, require_http_methods
from .views import rcon_api

logger = logging.getLogger("rconweb")


class DocumentForm(forms.Form):
    docfile = forms.FileField(label="Select a file")


@csrf_exempt
@login_required()
@permission_required("api.can_upload_vip_list", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
@require_content_type(["multipart/form-data"])
def upload_vips(request):
    errors = []
    send_to_discord_audit(
        message="upload_vips", command_name="upload_vips", by=request.user.username
    )
    vips = []
    seen = set()
    vietnam = rcon_api.config.game == GameEnum.HLL_VIETNAM
    for upload in request.FILES.values():
        for idx, raw in enumerate(upload, start=1):
            try:
                line = raw.decode("utf-8-sig").strip()
                if not line:
                    continue
                pid, name = line.split(maxsplit=1)
                eos = re.fullmatch(r"[0-9a-fA-F]{32}", pid)
                if not eos and (vietnam or not re.fullmatch(r"[0-9]{17}", pid)):
                    raise ValueError("Invalid game player ID")
                if pid.casefold() in seen:
                    raise ValueError("Duplicate player ID")
                expires = None
                parts = name.rsplit(maxsplit=1)
                # Older exports could contain an empty description before the ISO timestamp.
                if len(parts) == 1 and re.match(r"^\d{4}-\d{1,2}-\d{1,2}", name):
                    expires = parser.isoparse(name)
                    name = pid
                elif len(parts) == 2 and (not parts[1].isdigit() or len(parts[1]) == 8):
                    try:
                        expires = parser.parse(parts[1])
                    except (ValueError, OverflowError):
                        if re.match(r"^\d{4}-\d{1,2}-", parts[1]):
                            raise ValueError("Invalid expiration date")
                    else:
                        name = parts[0]
                seen.add(pid.casefold())
                vips.append((name, pid, expires))
            except (ValueError, OverflowError) as exc:
                errors.append(f"{upload.name} #{idx}: {exc}")
    if not vips and not errors:
        errors.append("No VIPs submitted")
    if errors:
        return api_response(result=None, failed=True, error="\n".join(errors), command="upload_vips")

    job_key = f"upload_vip_{os.getenv('SERVER_NUMBER')}"
    result = "Job submitted, will take several minutes"
    if request.POST.get("track_job") == "1":
        upload_id = uuid4().hex
        job_key += f"_{upload_id}"
        result = {"upload_id": upload_id}
    worker_bulk_vip(vips, job_key=job_key, mode="override")
    return api_response(result=result, failed=False, command="upload_vips")


@csrf_exempt
@login_required()
@permission_required("api.can_upload_vip_list", raise_exception=True)
@require_http_methods(["GET"])
def upload_vips_result(request):
    job_key = f"upload_vip_{os.getenv('SERVER_NUMBER')}"
    if upload_id := request.GET.get("upload_id"):
        if not re.fullmatch(r"[0-9a-f]{32}", upload_id):
            return api_response(error="Invalid upload ID", status_code=400)
        job_key += f"_{upload_id}"
    return api_response(
        result=get_job_results(job_key),
        failed=False,
        command="upload_vips_result",
    )


@csrf_exempt
@login_required()
@permission_required("api.can_download_vip_list", raise_exception=True)
@require_http_methods(["GET"])
def download_vips(request):
    now = datetime.datetime.now(datetime.timezone.utc)
    vip_lines = []
    for pid, entry in sorted(inventory(rcon_api).items()):
        expires = entry.expires or INDEFINITE_VIP_DATE
        if entry.listed or expires > now:
            name = " ".join((entry.name or pid).splitlines()).strip() or pid
            vip_lines.append(f"{pid} {name} {expires.isoformat()}")

    response = HttpResponse(
        "\n".join(vip_lines),
        content_type="text/plain",
    )

    response["Content-Disposition"] = (
        f"attachment; filename={datetime.datetime.now().isoformat()}_vips.txt"
    )
    return response
