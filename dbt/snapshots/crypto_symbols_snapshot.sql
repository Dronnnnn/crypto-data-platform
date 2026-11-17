{% snapshot crypto_symbols_snapshot %}
{{ config(
    target_schema=target.schema ~ '_snapshots',
    unique_key='symbol',
    strategy='check',
    check_cols=['base_asset', 'quote_asset', 'asset_name', 'is_active'],
    hard_deletes='invalidate'
) }}

SELECT symbol, base_asset, quote_asset, asset_name, is_active
FROM {{ ref('crypto_symbols') }}
{% endsnapshot %}
