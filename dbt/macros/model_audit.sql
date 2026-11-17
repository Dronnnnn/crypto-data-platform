{% macro model_audit_relation() %}
    {{ return(api.Relation.create(database=this.database, schema=this.schema,
                                  identifier='dbt_model_run_audit')) }}
{% endmacro %}

{% macro create_model_audit_table() %}
    CREATE TABLE IF NOT EXISTS {{ model_audit_relation() }} (
        model_name VARCHAR(256) NOT NULL,
        invocation_id VARCHAR(64) NOT NULL,
        recorded_at TIMESTAMP NOT NULL
    ) DISTSTYLE AUTO
{% endmacro %}

{% macro audit_model_success() %}
    -- Default transactional post_hook: INSERT and model commit together.
    -- No COUNT(*) scan, and no claim about affected rows or test success.
    INSERT INTO {{ model_audit_relation() }} (model_name, invocation_id, recorded_at)
    VALUES ('{{ this.identifier }}', '{{ invocation_id }}', GETDATE())
{% endmacro %}
