{
    "name": "XINXU Branding",
    "version": "18.0.1.0.0",
    "summary": "XINXU visual identity: company logo on the apps home screen "
               "and a branded browser tab title.",
    "author": "Mohamed Ali - XINXU Company",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": ["web", "web_responsive"],
    "data": [
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "xinxu_branding/static/src/scss/navbar_variables.scss",
        ],
        "web.assets_backend": [
            "xinxu_branding/static/src/components/apps_menu_logo.xml",
            "xinxu_branding/static/src/components/apps_menu_logo.scss",
            "xinxu_branding/static/src/js/browser_title.js",
        ],
    },
    "installable": True,
    "application": False,
}
