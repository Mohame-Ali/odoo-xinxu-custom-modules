# -*- coding: utf-8 -*-
import json
import time

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_html(self, report_ref, docids, data=None, **kwargs):
        html, content_type = super()._render_qweb_html(report_ref, docids, data=data, **kwargs)

        if report_ref in {
            "custom_invoice_xinxu.report_xinxu_proforma_local_document",
            "custom_invoice_xinxu.report_xinxu_proforma_foreign_document",
        }:
            # #region agent log
            try:
                payload = {
                    "sessionId": "cd0f01",
                    "runId": "pre-fix",
                    "hypothesisId": "H1-template-not-updated",
                    "location": "custom_invoice_xinxu/models/ir_actions_report.py:_render_qweb_html",
                    "message": "QWeb report rendered (HTML probe)",
                    "data": {
                        "report_ref": report_ref,
                        "docids_len": len(docids or []),
                        "has_colgroup": "<colgroup>" in (html or ""),
                        "colgroup_count": (html or "").count("<colgroup>"),
                        "has_table_layout_fixed": "table-layout: fixed" in (html or ""),
                        "table_layout_fixed_count": (html or "").count("table-layout: fixed"),
                    },
                    "timestamp": int(time.time() * 1000),
                }
                with open("/opt/odoo/.cursor/debug-cd0f01.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion

        return html, content_type

