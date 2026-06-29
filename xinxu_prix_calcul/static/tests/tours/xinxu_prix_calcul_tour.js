/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * Étape utilitaire : basculer en vue liste puis cliquer "Nouveau".
 * Fonctionne que la vue par défaut soit Kanban ou Liste.
 */
function switchToListAndCreate() {
    // 1) Forcer la vue liste
    const listBtn = document.querySelector(
        ".o_view_switcher button[data-view-type='list']"
    );
    if (listBtn && !listBtn.classList.contains("active")) {
        listBtn.click();
    }
    // 2) Trouver le bouton "Nouveau" — sélecteurs possibles en Odoo 17
    const newButton =
        document.querySelector(".o_list_button_add") ||
        document.querySelector("button.o_form_button_new") ||
        document.querySelector(".o-kanban-button-new") ||
        [...document.querySelectorAll("button")].find(
            (b) => b.textContent.trim().toLowerCase() === "new" ||
                   b.textContent.trim() === "Nouveau"
        );
    if (newButton) {
        newButton.click();
    }
}

registry.category("web_tour.tours").add("xinxu_prix_calcul_tour", {
    url: "/odoo/sales?view_type=list",
    steps: () => [
        {
            content: "Passer en vue liste et créer un nouveau devis",
            trigger: ".o_view_controller",
            run: switchToListAndCreate,
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
            content: "Sélectionner le type de calcul Local",
            trigger: ".o_field_widget[name='xinxu_calc_type'] .o_radio_item label:first",
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
            content: "Vérifier que le Prix TTC est calculé",
            trigger: ".o_field_widget[name='x_prix_ttc']",
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