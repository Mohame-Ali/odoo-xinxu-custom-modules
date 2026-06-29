/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("xinxu_prix_calcul_tour_foreign", {
    url: "/odoo/sales",
    steps: () => [
        {
            content: "Attendre la vue liste des devis",
            trigger: ".o_sale_order",
        },
        {
            content: "Créer un nouveau devis",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Attendre le formulaire de devis",
            trigger: ".o_form_view .o_field_widget[name='partner_id']",
        },
        {
            content: "Saisir le nom du client",
            trigger: ".o_form_view .o_field_widget[name='partner_id'] input",
            run: "edit XINXU E2E Client",
        },
        {
            content: "Sélectionner le client dans le dropdown",
            trigger: ".dropdown-item:contains('XINXU E2E Client')",
            run: "click",
        },
        {
            content: "Sélectionner le type de calcul Foreign",
            trigger: ".o_field_widget[name='xinxu_calc_type'] .o_radio_item label:last",
            run: "click",
        },
        {
            content: "Ouvrir l'onglet Tableau de Calcul",
            trigger: ".o_notebook .nav-link:contains('Tableau de Calcul')",
            run: "click",
        },
        {
            content: "Attendre que l'onglet Tableau de Calcul soit actif",
            trigger: ".o_notebook .nav-link.active:contains('Tableau de Calcul')",
        },
        {
            content: "Ajouter une ligne dans le Tableau de Calcul",
            trigger: ".o_field_one2many[name='order_line'] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            content: "Saisir le produit",
            trigger: ".o_selected_row .o_field_widget[name='product_id'] input",
            run: "edit XINXU E2E Product",
        },
        {
            content: "Valider la sélection du produit",
            trigger: ".dropdown-item:contains('XINXU E2E Product')",
            run: "click",
        },
        {
            content: "Saisir le prix fournisseur",
            trigger: ".o_field_widget[name='x_supplier_price'] input",
            run: "edit 100",
        },
        {
            content: "Valider la saisie",
            trigger: ".o_form_statusbar",
            run: "click",
        },
        {
            content: "Confirmer le devis",
            trigger: "button[name='action_confirm']",
            run: "click",
        },
        {
            content: "Vérifier que le devis est confirmé",
            trigger: "button[name='action_xinxu_create_purchase_order']",
        },
    ],
});