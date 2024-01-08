import ucsschool_id_connector.utils


def test_deprecation_updates():
    get_app_version_result = ucsschool_id_connector.utils.get_app_version()
    if get_app_version_result >= "4":
        # src/schedule_* scripte removed?
        raise Exception(
            "Please check that the src/schedule_* scripts have been removed. "
            "Remove this exception afterwards."
            "See Issue univention/components/ucsschool-id-connector#52."
        )
