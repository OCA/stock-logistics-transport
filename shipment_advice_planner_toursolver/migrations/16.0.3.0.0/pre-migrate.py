import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    cr = env.cr
    _logger.info("Migrating toursolver backend options")
    _logger.info(
        "Rename colmumn rqst_options_properties_definition to options_definition"
    )
    openupgrade.rename_columns(
        cr,
        {
            "toursolver_backend_option_definition": [
                ("backend_options_definition", "options_definition")
            ]
        },
    )

    _logger.info(
        "Rename model toursolver_backend_option_definition "
        "to toursolver_request_props_definition"
    )
    openupgrade.rename_models(
        cr,
        [
            (
                "toursolver.backend.option.definition",
                "toursolver.request.props.definition",
            )
        ],
    )
    openupgrade.rename_tables(
        cr,
        [
            (
                "toursolver_backend_option_definition",
                "toursolver_request_props_definition",
            )
        ],
    )

    _logger.info("Rename column backend_option to rqst_options_properties")
    openupgrade.rename_columns(
        cr, {"toursolver_backend": [("backend_options", "rqst_options_properties")]}
    )
