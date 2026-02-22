        # ... (lines 1-1024)
    def GenerateReportBundle(self, request, context):
        import zipfile

        if request is None:
            return pb2.GenerateReportBundleResponse(success=False, message="Missing request")

        try:
            converter = MmToJsonConverter(table_data=self._data_cache)
            extractor = ReportDataExtractor(converter)

            rtype_map = {
                pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
                pb2.REPORT_TYPE_ENTRIES: "entries",
                pb2.REPORT_TYPE_LINEUPS: "lineups",
                pb2.REPORT_TYPE_RESULTS: "results",
                pb2.REPORT_TYPE_MEET_PROGRAM: "program",
                pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
                pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
                pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
            }

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, report_req in enumerate(request.reports):
                    rtype_val = report_req.type
                    rtype = rtype_map.get(rtype_val, "psych")
                    title = report_req.title
                    team_filter = report_req.team_filter
                    gender_filter = report_req.gender_filter
                    age_group_filter = report_req.age_group_filter

                    # New variation fields
                    columns_on_page = 2
                    if report_req.columns_on_page:
                        columns_on_page = report_req.columns_on_page

                    show_relay_swimmers = True
                    if report_req.HasField("show_relay_swimmers"):
                        show_relay_swimmers = report_req.show_relay_swimmers

                    zebra_striping = False
                    if report_req.HasField("zebra_striping"):
                        zebra_striping = report_req.zebra_striping

                    lane_filter = None
                    if report_req.HasField("lane_filter"):
                        lane_filter = report_req.lane_filter

                    show_dq_lines = False
                    if report_req.HasField("show_dq_lines"):
                        show_dq_lines = report_req.show_dq_lines

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        temp_path = tmp.name

                    renderer = WeasyRenderer(temp_path)

                    if rtype == "psych":
                        report_data = extractor.extract_psych_sheet_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "psych_sheet.j2")
                    elif rtype == "entries":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_hytek.j2")
                    elif rtype == "lineups":
                        report_data = extractor.extract_timer_sheets_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                            lane_filter=lane_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "lineups.j2")
                    elif rtype == "results":
                        report_data = extractor.extract_results_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "results.j2")
                    elif rtype == "program":
                        program_data = extractor.extract_meet_program_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                            columns_on_page=columns_on_page,
                            show_relay_swimmers=show_relay_swimmers,
                            show_dq_lines=show_dq_lines,
                        )
                        program_data["zebra_striping"] = zebra_striping
                        renderer.render_meet_program(program_data)
                    elif rtype == "program_html":
                        program_data = extractor.extract_meet_program_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                            columns_on_page=columns_on_page,
                            show_relay_swimmers=show_relay_swimmers,
                        )
                        program_data["zebra_striping"] = zebra_striping
                        html_content = renderer.render_to_html(program_data)
                        with open(temp_path, "w") as f:
                            f.write(html_content)
                    elif rtype == "entries_hytek":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_hytek.j2")
                    elif rtype == "entries_club":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_club.j2")

                    if os.path.exists(temp_path):
                        # Clean title for filename
                        safe_title = "".join(c for c in (title or rtype) if c.isalnum() or c in (" ", "_", "-")).strip()
                        ext = ".html" if rtype == "program_html" else ".pdf"
                        file_name = f"{idx + 1}_{safe_title}{ext}"
                        zip_file.write(temp_path, file_name)
                        os.remove(temp_path)

            bundle_name = request.bundle_name or f"meet_bundle_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            if not bundle_name.endswith(".zip"):
                bundle_name += ".zip"

            return pb2.GenerateReportBundleResponse(
                success=True,
                message="Bundle generated successfully",
                zip_content=zip_buffer.getvalue(),
                filename=bundle_name,
            )

        except Exception as e:
            print(f"Error generating report bundle: {e}")
            return pb2.GenerateReportBundleResponse(success=False, message=str(e))
