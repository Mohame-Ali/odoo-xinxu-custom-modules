/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useService, useBus } from "@web/core/utils/hooks";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        const titleService = useService("title");
        const brand = "XINXU ERP";
        titleService.setParts({ zopenerp: brand });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            titleService.setParts({ zopenerp: brand });
        });
    },
});
