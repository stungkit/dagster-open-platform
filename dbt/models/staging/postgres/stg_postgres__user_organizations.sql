select distinct

    id as user_organization_id,
    organization_id,
    user_id,
    create_timestamp as created_at,
    activated as is_activated

from {{ source('postgres_etl_low_freq', 'users_organizations') }}
