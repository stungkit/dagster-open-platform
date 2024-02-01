select

    organization_id,
    deployment_id,
    split_part(opaque_id, ':', -1) as opaque_id,
    metric_name,
    max_by(cost, last_updated) as cost,
    max(last_updated) as last_updated

from {{ source('purina_staging', 'insights_metrics_submissions') }}

group by 1, 2, 3, 4