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
    msgpack_path,  # Use msgpack file instead of large dict
    rtype_map,
    renderer_type=None,
    html_preview=False,
):
    # This runs in a separate process, avoiding the GIL
    import datetime
    import logging
    import os
    import tempfile
    import traceback

    import msgpack

    # Re-initialize logging configuration in the subprocess to ensure logs are captured
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)

    # Suppress verbose third-party loggers in the subprocess
    if log_level_str != "DEBUG":
        logging.getLogger("fontTools").setLevel(logging.WARNING)
        logging.getLogger("fontTools.subset").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
        logging.getLogger("jpype").setLevel(logging.WARNING)
        # Also disable global logging for anything below INFO to catch stray loggers
        logging.disable(logging.DEBUG)

    from meetmanager.v1 import meet_manager_pb2 as pb2
    from mm_to_json.mm_to_json import MmToJsonConverter
    from mm_to_json.reporting.extractor import ReportDataExtractor
    from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer
    from mm_to_json.reporting.weasy_renderer import WeasyRenderer

    rtype = rtype_map.get(report_req_type, "psych")
    title = report_req_title

    start_time = datetime.datetime.now()

    with open(msgpack_path, "rb") as f:
        packed_data = msgpack.unpack(f, raw=False)

    cache_data = packed_data["cache"]
    full_data = packed_data["full_data"]

    load_end_time = datetime.datetime.now()
    load_duration = (load_end_time - start_time).total_seconds()

    converter = MmToJsonConverter(table_data=cache_data)
    extractor = ReportDataExtractor(converter, full_data=full_data)

    is_html = html_preview or rtype == "program_html"
    with tempfile.NamedTemporaryFile(suffix=".html" if is_html else ".pdf", delete=False) as tmp:
        temp_path = tmp.name

    try:
        render_start_time = datetime.datetime.now()

        # Use requested renderer
        renderer: PlaywrightRenderer | WeasyRenderer
        if renderer_type == pb2.RENDERER_TYPE_PLAYWRIGHT:
            renderer = PlaywrightRenderer(temp_path)
        else:
            renderer = WeasyRenderer(temp_path)

        report_data = None
        template = "meet_program.j2"

        if rtype == "psych":
            report_data = extractor.extract_psych_sheet_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "psych_sheet.j2"
        elif rtype in ["entries", "entries_hytek"]:
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "entries_hytek.j2"
        elif rtype == "lineups":
            report_data = extractor.extract_timer_sheets_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "timer_sheets.j2"
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

        if report_data:
            report_data["zebra_striping"] = zebra_striping
            if is_html:
                html_content = renderer.render_to_html(report_data, template_name=template)
                with open(temp_path, "wb") as f:
                    f.write(html_content.encode("utf-8"))
            else:
                if template == "meet_program.j2":
                    renderer.render_meet_program(report_data)
                else:
                    renderer.render_entries(report_data, template)

        if os.path.exists(temp_path):
            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(temp_path)
        else:
            pdf_bytes = b""

        render_duration = (datetime.datetime.now() - render_start_time).total_seconds()

        # Determine the effective filename
        ext = ".html" if is_html else ".pdf"
        final_filename = f"{user_id}_{title}{ext}"

        # If it was an HTML preview, we also want to return the string for convenience
        html_str = ""
        if is_html:
            html_str = pdf_bytes.decode("utf-8")

        return {
            "pdf_bytes": pdf_bytes,
            "filename": final_filename,
            "html_content": html_str,
            "load_duration": load_duration,
            "render_duration": render_duration,
        }

    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        logging.error(f"Error in single report process: {e}")
        logging.error(traceback.format_exc())
        raise e
