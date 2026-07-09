from __future__ import annotations

import datetime
import io
import json
import logging
import multiprocessing
import os
import sys
import tempfile
import threading
import zipfile
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Protocol, cast

import grpc
import msgpack

if TYPE_CHECKING:
    from server import JobManager
    from storage_provider import StorageProvider


class ReportServicerContext(Protocol):
    storage: StorageProvider
    job_manager: JobManager
    _user_cache: OrderedDict[str, dict[str, Any]]

    def _check_auth(self, context: grpc.ServicerContext) -> str: ...
    def _load_user_data(self, context: grpc.ServicerContext) -> tuple[dict[str, Any], dict[str, Any]]: ...


SOURCE_FILE = "Sample_Data.json"


# Configure logging in local Pacific Time (PT) for California
def pacific_time_converter(*args):
    import datetime
    import time

    secs = args[-1] if args else time.time()
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo("America/Los_Angeles")
        dt = datetime.datetime.fromtimestamp(secs, tz=tz)
        return dt.timetuple()
    except Exception:
        return time.localtime(secs)


logging.Formatter.converter = pacific_time_converter


def msgpack_encode(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable in msgpack")


def _process_single_report_process(
    report_req_type,
    report_req_title,
    report_req_team_filter,
    report_req_gender_filter,
    report_req_age_group_filter,
    user_id,
    columns_on_page,
    show_relay_swimmers,
    zebra_striping,
    msgpack_path,
    rtype_map,
    renderer_type=None,
    html_preview=False,
    idx=0,
    user_email=None,
    include_blank_lanes=True,
    break_every_six_events=True,
):
    import datetime
    import logging
    import os
    import tempfile
    import traceback

    from mm_to_json.platform_setup import setup_platform_env

    setup_platform_env()

    import msgpack

    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)
    logging.Formatter.converter = pacific_time_converter
    if log_level_str != "DEBUG":
        logging.getLogger("fontTools").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
    from mm_to_json.reporting.extractor import ReportDataExtractor

    rtype = rtype_map.get(report_req_type, "psych")
    title = report_req_title
    start_time = datetime.datetime.now()
    try:
        with open(msgpack_path, "rb") as f:
            unpacked = msgpack.unpack(f, raw=False)
            full_data = unpacked["full_data"]
            cache_data = unpacked["cache"]
        load_duration = (datetime.datetime.now() - start_time).total_seconds()
        render_start_time = datetime.datetime.now()
        is_html = html_preview or (rtype == "program_html")
        temp_fd, temp_path = tempfile.mkstemp(suffix=".html" if is_html else ".pdf")
        os.close(temp_fd)

        from mm_to_json.mm_to_json import MmToJsonConverter

        converter = MmToJsonConverter(table_data=cache_data)
        extractor = ReportDataExtractor(converter, full_data=full_data)
        renderer: Any = None
        is_playwright = False
        if renderer_type is not None:
            if isinstance(renderer_type, str):
                is_playwright = renderer_type.lower() in ["playwright", "renderer_type_playwright"]
            elif isinstance(renderer_type, int):
                is_playwright = renderer_type == 2
            else:
                is_playwright = "playwright" in str(renderer_type).lower()

        if is_playwright:
            from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer

            renderer = PlaywrightRenderer(output_path=temp_path)
        else:
            from mm_to_json.reporting.weasy_renderer import WeasyRenderer

            renderer = WeasyRenderer(output_path=temp_path)

        report_data = None
        if rtype == "psych":
            report_data = extractor.extract_psych_sheet_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "psych_sheet.j2"
        elif rtype == "entries" or rtype == "entries_hytek":
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "entries_hytek.j2"
        elif rtype == "lineups":
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "lineups.j2"
        elif rtype == "results":
            report_data = extractor.extract_results_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "results.j2"
        elif rtype == "entries_club":
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "entries_club.j2"
        elif rtype == "lane_timer_sheets":
            report_data = extractor.extract_lane_timer_sheets_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
                include_blank_lanes=include_blank_lanes,
                break_every_six_events=break_every_six_events,
            )
            template = "timer_sheets.j2"
        elif rtype in ["program", "program_html", "judge_sheets"]:
            report_data = extractor.extract_meet_program_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
                columns_on_page=columns_on_page,
                show_relay_swimmers=show_relay_swimmers,
                show_dq_lines=(rtype == "judge_sheets"),
            )
            template = "meet_program.j2"
        elif rtype == "cts_export":
            from mm_to_json.reporting.cts_writer import CTSScoreboardWriter

            all_events = []
            for session in full_data.get("sessions", []):
                all_events.extend(session.get("events", []))

            with tempfile.TemporaryDirectory() as cts_tmp_dir:
                writer = CTSScoreboardWriter(full_data, all_events)
                writer.generate_all(cts_tmp_dir)

                files = []
                for fname in os.listdir(cts_tmp_dir):
                    with open(os.path.join(cts_tmp_dir, fname), "rb") as f_read:
                        files.append({"filename": fname, "content": f_read.read()})

                return {
                    "success": True,
                    "files": files,
                    "rtype": rtype,
                    "idx": idx,
                    "load_duration": load_duration,
                    "render_duration": 0,
                }
        elif rtype == "check_in_sheet":
            from mm_to_json.reporting.check_in_writer import SwimmerCheckInWriter

            check_in_data = extractor.extract_check_in_data(team_filter=report_req_team_filter)

            gs_url = None
            if user_email:
                try:
                    gs_writer = SwimmerCheckInWriter(check_in_data, title=title)
                    gs_url = gs_writer.generate_google_sheet(user_email=user_email)
                except Exception as e:
                    logging.warning(f"Google Sheet generation failed, but will still provide Excel backup: {e}")

            xlsx_tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
            xlsx_tmp.close()
            try:
                excel_writer = SwimmerCheckInWriter(check_in_data, title=title)
                excel_writer.generate_excel_backup(xlsx_tmp.name)
                with open(xlsx_tmp.name, "rb") as f_read:
                    content = f_read.read()
            finally:
                if os.path.exists(xlsx_tmp.name):
                    os.unlink(xlsx_tmp.name)

            res_files = []
            filename = f"{title.replace(' ', '_')}_{idx}.xlsx" if title else f"check_in_{idx}.xlsx"
            res_files.append({"filename": filename, "content": content})

            if gs_url:
                shortcut_name = f"OPEN_GOOGLE_SHEET_{filename.replace('.xlsx', '.html')}"
                html_tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
                html_tmp.close()
                try:
                    shortcut_writer = SwimmerCheckInWriter(check_in_data, title=title)
                    shortcut_writer.generate_google_sheet_shortcut(gs_url, html_tmp.name)
                    with open(html_tmp.name, "rb") as f_read:
                        shortcut_content = f_read.read()
                finally:
                    if os.path.exists(html_tmp.name):
                        os.unlink(html_tmp.name)
                res_files.append({"filename": shortcut_name, "content": shortcut_content})

            return {
                "success": True,
                "files": res_files,
                "content": content,
                "filename": filename,
                "message": f"Google Sheet: {gs_url}" if gs_url else "Excel Backup generated",
                "gs_url": gs_url,
                "rtype": rtype,
                "idx": idx,
                "load_duration": load_duration,
                "render_duration": 0,
            }
        if report_data:
            report_data["zebra_striping"] = zebra_striping
            if is_html:
                html_content = renderer.render_to_html(report_data, template_name=template)
                with open(temp_path, "wb") as f_write:
                    f_write.write(html_content.encode("utf-8"))
            else:
                if template == "meet_program.j2":
                    renderer.render_meet_program(report_data)
                else:
                    renderer.render_entries(report_data, template)
        if os.path.exists(temp_path):
            with open(temp_path, "rb") as f_read:
                pdf_bytes = f_read.read()
            os.unlink(temp_path)
        else:
            pdf_bytes = b""
        render_duration = (datetime.datetime.now() - render_start_time).total_seconds()
        ext = ".html" if is_html else ".pdf"

        safe_title = "".join(c for c in (title or rtype) if c.isalnum() or c in (" ", "_", "-")).strip()
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        final_filename = f"{safe_title}_{timestamp}{ext}"

        html_str = pdf_bytes.decode("utf-8") if is_html else ""
        return {
            "success": True,
            "content": pdf_bytes,
            "filename": final_filename,
            "html_content": html_str,
            "rtype": rtype,
            "idx": idx,
            "load_duration": load_duration,
            "render_duration": render_duration,
        }
    except Exception as e:
        logging.error(f"Error in _process_single_report_process (idx {idx}): {traceback.format_exc()}")
        return {"success": False, "error": str(e), "rtype": rtype, "idx": idx}


def generate_report(request: Any, context: grpc.ServicerContext, servicer: ReportServicerContext, pb2: Any) -> Any:
    """Synchronously generates a single PDF/HTML report."""
    request = request or pb2.GenerateReportRequest()
    try:
        try:
            uid = getattr(context, "uid", None)
            if uid is None and context:
                try:
                    metadata = dict(context.invocation_metadata())
                    uid = metadata.get("x-user-id")
                except Exception:
                    pass

            if uid is None:
                if os.getenv("GRPC_AUTH_DISABLED") == "true" or not os.getenv("K_SERVICE"):
                    uid = "dev-user"

            if uid:
                cache, _ = servicer._load_user_data(context)
            else:
                raise ValueError("No authentication")
        except Exception:
            if getattr(sys, "frozen", False):
                sample_path = os.path.join(getattr(sys, "_MEIPASS", ""), "data", SOURCE_FILE)
            else:
                sample_path = os.path.join(os.path.dirname(__file__), "..", "data", SOURCE_FILE)
            with open(sample_path) as f:
                cache = json.load(f)

        rtype_map = {
            pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
            pb2.REPORT_TYPE_ENTRIES: "entries",
            pb2.REPORT_TYPE_LINEUPS: "lineups",
            pb2.REPORT_TYPE_RESULTS: "results",
            pb2.REPORT_TYPE_MEET_PROGRAM: "program",
            pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
            pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
            pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
            pb2.REPORT_TYPE_LANE_TIMER_SHEETS: "lane_timer_sheets",
            pb2.REPORT_TYPE_JUDGE_SHEETS: "judge_sheets",
            pb2.REPORT_TYPE_CTS_EXPORT: "cts_export",
            pb2.REPORT_TYPE_CHECK_IN_SHEET: "check_in_sheet",
        }

        from handlers.auth_utils import get_user_email
        from mm_to_json.mm_to_json import MmToJsonConverter

        converter = MmToJsonConverter(table_data=cache)
        full_data = converter.convert()

        with tempfile.NamedTemporaryFile(suffix=".msgpack", delete=False) as msgpack_tmp:
            msgpack_path = msgpack_tmp.name
            msgpack.pack({"full_data": full_data, "cache": cache}, msgpack_tmp, default=msgpack_encode)

        user_email = get_user_email(cast(str, uid))

        try:
            res = _process_single_report_process(
                request.type,
                request.title,
                request.team_filter,
                request.gender_filter,
                request.age_group_filter,
                uid,
                request.columns_on_page if request.HasField("columns_on_page") else 2,
                request.show_relay_swimmers if request.HasField("show_relay_swimmers") else True,
                request.zebra_striping if request.HasField("zebra_striping") else False,
                msgpack_path,
                rtype_map,
                request.renderer_type if hasattr(request, "renderer_type") else None,
                getattr(request, "html_preview", False),
                idx=0,
                user_email=user_email,
                include_blank_lanes=request.include_blank_lanes if request.HasField("include_blank_lanes") else True,
                break_every_six_events=request.break_every_six_events
                if request.HasField("break_every_six_events")
                else True,
            )
        finally:
            if os.path.exists(msgpack_path):
                os.remove(msgpack_path)

        if not res["success"]:
            logging.error(f"Report generation failed in worker: {res.get('error')}")
            return pb2.GenerateReportResponse(success=False, message=res["error"])

        content_bytes = b""
        filename = ""
        html_str = ""

        if "files" in res:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for f in res["files"]:
                    zip_file.writestr(f["filename"], f["content"])
            content_bytes = zip_buffer.getvalue()
            filename = f"{res['rtype']}_export.zip"
        else:
            content_bytes = res["content"]
            filename = res["filename"]
            if filename.endswith(".html"):
                html_str = content_bytes.decode("utf-8")

        logging.info(f"Report generated: {filename} ({len(content_bytes)} bytes)")

        return pb2.GenerateReportResponse(
            success=True,
            message="Report generated successfully",
            pdf_content=content_bytes if not filename.endswith(".html") else b"",
            filename=filename,
            html_content=html_str if html_str else None,
            google_sheet_url=res.get("gs_url"),
        )
    except Exception as e:
        logging.error(f"Error generating report: {e}")
        return pb2.GenerateReportResponse(success=False, message=str(e))


def _run_bundle_generation_job(
    job_id: str, request: Any, uid: str, cache: dict[str, Any], servicer: ReportServicerContext, pb2: Any
):
    """Background worker for report bundle generation."""
    logging.info(f"Background thread started for job {job_id}")
    try:
        servicer.job_manager.update_job(job_id, status=pb2.JOB_STATUS_PROCESSING, message="Converting data...")
        logging.info(f"Job {job_id}: starting MmToJsonConverter")
        rtype_map = {
            pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
            pb2.REPORT_TYPE_ENTRIES: "entries",
            pb2.REPORT_TYPE_LINEUPS: "lineups",
            pb2.REPORT_TYPE_RESULTS: "results",
            pb2.REPORT_TYPE_MEET_PROGRAM: "program",
            pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
            pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
            pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
            pb2.REPORT_TYPE_LANE_TIMER_SHEETS: "lane_timer_sheets",
            pb2.REPORT_TYPE_JUDGE_SHEETS: "judge_sheets",
            pb2.REPORT_TYPE_CTS_EXPORT: "cts_export",
            pb2.REPORT_TYPE_CHECK_IN_SHEET: "check_in_sheet",
        }

        from handlers.auth_utils import get_data_access_token, get_user_email
        from mm_to_json.mm_to_json import MmToJsonConverter

        converter = MmToJsonConverter(table_data=cache)
        full_data = converter.convert()

        num_events = sum(len(s.get("events", [])) for s in full_data.get("sessions", []))
        logging.info(f"Job {job_id}: data conversion complete. {num_events} events found.")

        with tempfile.NamedTemporaryFile(suffix=".msgpack", delete=False) as msgpack_tmp:
            msgpack_path = msgpack_tmp.name
            msgpack.pack({"full_data": full_data, "cache": cache}, msgpack_tmp, default=msgpack_encode)
            msgpack_tmp.flush()
            msgpack_tmp.close()

        tasks = []
        env_max_workers = os.getenv("REPORT_MAX_WORKERS")
        if env_max_workers:
            try:
                max_workers = int(env_max_workers)
            except ValueError:
                max_workers = 3
        elif os.getenv("K_SERVICE"):
            max_workers = 3  # Cloud Run CPU limit safety
        else:
            max_workers = min(os.cpu_count() or 4, 8)

        servicer.job_manager.update_job(job_id, progress=0.05, message=f"Rendering {len(request.reports)} reports...")
        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            from concurrent.futures import ThreadPoolExecutor

            logging.info(
                f"Job {job_id}: running in frozen environment. Using ThreadPoolExecutor with {max_workers} workers."
            )
            executor_class = ThreadPoolExecutor
            executor_kwargs = {"max_workers": max_workers}
        else:
            logging.info(f"Job {job_id}: starting ProcessPoolExecutor with {max_workers} workers")
            executor_class = ProcessPoolExecutor
            ctx = multiprocessing.get_context("spawn")
            executor_kwargs = {"max_workers": max_workers, "mp_context": ctx}

        try:
            report_reqs = list(request.reports)
            user_email = get_user_email(uid)

            with executor_class(**executor_kwargs) as executor:
                for idx, report_req in enumerate(report_reqs):
                    tasks.append(
                        executor.submit(
                            _process_single_report_process,
                            report_req.type,
                            report_req.title,
                            report_req.team_filter,
                            report_req.gender_filter,
                            report_req.age_group_filter,
                            uid,
                            report_req.columns_on_page if getattr(report_req, "columns_on_page", None) else 2,
                            report_req.show_relay_swimmers if report_req.HasField("show_relay_swimmers") else True,
                            report_req.zebra_striping if report_req.HasField("zebra_striping") else False,
                            msgpack_path,
                            rtype_map,
                            request.renderer_type if hasattr(request, "renderer_type") else None,
                            False,
                            idx,
                            user_email,
                            include_blank_lanes=report_req.include_blank_lanes
                            if report_req.HasField("include_blank_lanes")
                            else True,
                            break_every_six_events=report_req.break_every_six_events
                            if report_req.HasField("break_every_six_events")
                            else True,
                        )
                    )

            total_reports = len(tasks)
            finished_count = 0

            for _ in as_completed(tasks):
                finished_count += 1
                progress = 0.05 + (0.90 * (finished_count / total_reports))
                servicer.job_manager.update_job(
                    job_id, progress=progress, message=f"Generated {finished_count}/{total_reports} reports"
                )
                logging.info(f"Job {job_id}: Progress update {finished_count}/{total_reports}")

            zip_buffer = io.BytesIO()
            gs_urls = []
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for i, future in enumerate(tasks):
                    res = future.result()
                    if res.get("success"):
                        if "gs_url" in res and res["gs_url"]:
                            gs_urls.append(res["gs_url"])

                        if "files" in res:
                            for f in res["files"]:
                                zip_file.writestr(f"CTS_Export/{f['filename']}", f["content"])
                        else:
                            zip_file.writestr(res["filename"], res["content"])

                        logging.info(
                            f"Job {job_id}: Report {i + 1}/{total_reports} ({res.get('rtype')}) added to bundle"
                        )
                    else:
                        raise Exception(
                            f"Failed to generate report {res.get('idx')} ({res.get('rtype')}): {res['error']}"
                        )
        finally:
            if os.path.exists(msgpack_path):
                os.remove(msgpack_path)

        servicer.job_manager.update_job(job_id, message="Uploading bundle...")

        num_reports = len(request.reports)
        bundle_name = (
            request.bundle_name
            or f"meet_bundle_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{num_reports}_items.zip"
        )
        if not bundle_name.endswith(".zip"):
            bundle_name += ".zip"

        bundle_rel_path = os.path.join("users", uid, "published", "bundles", bundle_name)

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as bundle_tmp:
            bundle_tmp.write(zip_buffer.getvalue())
            bundle_tmp_path = bundle_tmp.name
            bundle_tmp.close()

        try:
            servicer.storage.upload_file(bundle_tmp_path, bundle_rel_path)
        finally:
            if os.path.exists(bundle_tmp_path):
                os.remove(bundle_tmp_path)

        bundle_url = servicer.storage.get_url(bundle_rel_path)

        from urllib.parse import urlparse

        parsed_bundle = urlparse(bundle_url)
        is_relative = bundle_url.startswith("/")
        is_unsigned_gcs = (
            parsed_bundle.netloc == "storage.googleapis.com" or parsed_bundle.netloc == "storage.cloud.google.com"
        ) and not parsed_bundle.query

        if is_relative or is_unsigned_gcs:
            token = get_data_access_token()
            import urllib.parse

            safe_bundle_path = urllib.parse.quote(bundle_rel_path)
            frontend_base = getattr(request, "frontend_url", None) or os.getenv("FRONTEND_URL")
            if not frontend_base:
                frontend_base = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:3100")

            bundle_url = f"{frontend_base.rstrip('/')}/api/data?path={safe_bundle_path}&token={token}"
            logging.info(f"Using absolute proxy fallback URL: {bundle_url}")

        logging.info(f"Job {job_id}: Final bundle_url: {bundle_url}")

        servicer.job_manager.update_job(
            job_id,
            status=pb2.JOB_STATUS_COMPLETED,
            progress=1.0,
            message="Complete",
            bundle_url=bundle_url,
            google_sheet_urls=gs_urls,
        )

    except Exception as e:
        logging.error(f"Background job {job_id} failed: {e}")
        servicer.job_manager.update_job(job_id, status=pb2.JOB_STATUS_FAILED, message=str(e))


def generate_report_bundle(
    request: Any, context: grpc.ServicerContext, servicer: ReportServicerContext, pb2: Any
) -> Any:
    """Asynchronously generates a report bundle."""
    logging.info("GenerateReportBundle RPC called")
    try:
        uid = servicer._check_auth(context)
        if uid:
            cache, _ = servicer._load_user_data(context)
        else:
            raise ValueError("No authentication")
    except Exception:
        if getattr(sys, "frozen", False):
            sample_path = os.path.join(getattr(sys, "_MEIPASS", ""), "data", SOURCE_FILE)
        else:
            sample_path = os.path.join(os.path.dirname(__file__), "..", "data", SOURCE_FILE)
        with open(sample_path) as f:
            cache = json.load(f)
        uid = "sample-user"

    if request is None:
        return pb2.GenerateReportBundleResponse(success=False, message="Missing request")

    job_id = servicer.job_manager.create_job()
    logging.info(f"Created background job {job_id}")

    thread = threading.Thread(target=_run_bundle_generation_job, args=(job_id, request, uid, cache, servicer, pb2))
    thread.start()

    return pb2.GenerateReportBundleResponse(
        success=True,
        message="Bundle generation started",
        job_id=job_id,
    )
