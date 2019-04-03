blueprint = ""
operator_name = ""
operator_execution_arn = ""
operator_status_arn = ""
operator_failed_arn = ""
retry_seconds = ""
operator_enabled = ""
operator_media_type = ""

with open(blueprint, "r") as f:
    operator_blueprint = f.read()

new_file_name = operator_name + ".json"

with open(new_file_name, "w") as f:
    operator_blueprint = operator_blueprint.replace("%%OPERATOR_NAME%%", operator_name)
    operator_blueprint = operator_blueprint.replace("%%%EXECUTION_LAMBDA_ARN%%", operator_execution_arn)
    operator_blueprint = operator_blueprint.replace("%%GET_STATUS_LAMBDA_ARN%%", operator_status_arn)
    operator_blueprint = operator_blueprint.replace("%%RETRY_SECONDS%%", retry_seconds)
    operator_blueprint = operator_blueprint.replace("%%OPERATOR_ENABLED%%", operator_enabled)
    operator_blueprint = operator_blueprint.replace("%%OPERATOR_MEDIA_TYPE%%", operator_media_type)
    operator_blueprint = operator_blueprint.replace("%%FAILED_LAMBDA_ARN%%", operator_failed_arn)

    f.write(operator_blueprint)







