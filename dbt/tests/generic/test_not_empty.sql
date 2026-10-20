{% test not_empty(model) %}
SELECT COUNT(*) AS row_count
FROM {{ model }}
HAVING COUNT(*) = 0
{% endtest %}
