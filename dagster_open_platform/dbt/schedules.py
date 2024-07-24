from dagster import AssetSelection, RunRequest, ScheduleDefinition, define_asset_job, schedule
from dagster_dbt import DbtManifestAssetSelection
from dagster_open_platform.dbt.assets import CustomDagsterDbtTranslator, dbt_snapshot_models
from dagster_open_platform.dbt.partitions import insights_partition
from dagster_open_platform.dbt.resources import dagster_open_platform_dbt_project

######################################################
##              INSIGHTS                            ##
######################################################

insights_job = define_asset_job(
    name="insights_job",
    selection=(
        # select all insights models, and fetch upstream, including ingestion
        DbtManifestAssetSelection.build(
            manifest=dagster_open_platform_dbt_project.manifest_path,
            dagster_dbt_translator=CustomDagsterDbtTranslator(),
            select="tag:insights",
        )
        .upstream()
        .required_multi_asset_neighbors()
        - AssetSelection.groups("cloud_product_main")
        - AssetSelection.groups("cloud_product_shard1")
    ),
    partitions_def=insights_partition,
    tags={"team": "insights", "dbt_pipeline": "insights"},
)


@schedule(cron_schedule="0 */3 * * *", job=insights_job)
def insights_schedule():
    most_recent_partition = insights_partition.get_last_partition_key()
    yield RunRequest(partition_key=str(most_recent_partition), run_key=str(most_recent_partition))


######################################################
##              Main DBT Pipeline                   ##
######################################################

dbt_analytics_core_job = define_asset_job(
    name="dbt_analytics_core_job",
    selection=(
        DbtManifestAssetSelection.build(
            manifest=dagster_open_platform_dbt_project.manifest_path,
            dagster_dbt_translator=CustomDagsterDbtTranslator(),
        ).required_multi_asset_neighbors()
        - AssetSelection.groups(
            # insights groups
            "cloud_reporting",
        )
    ),
    tags={"team": "devrel", "dbt_pipeline": "analytics_core"},
)


# Cloud usage metrics isn't partitioned, but it uses a partitioned asset
# that is managed by Insights. It doesn't matter which partition runs
# but does need to specify the most recent partition of Insights will be run
@schedule(cron_schedule="0 3 * * *", job=dbt_analytics_core_job)
def dbt_analytics_core_schedule():
    most_recent_partition = insights_partition.get_last_partition_key()
    yield RunRequest(partition_key=str(most_recent_partition), run_key=str(most_recent_partition))


dbt_analytics_snapshot_schedule = ScheduleDefinition(
    job=define_asset_job(
        name="dbt_analytics_snapshot_job",
        selection=(AssetSelection.assets(dbt_snapshot_models)),
        tags={"team": "devrel"},
    ),
    cron_schedule="0 * * * *",
)


scheduled_jobs = [insights_job]


schedules = [
    insights_schedule,
    dbt_analytics_core_schedule,
    dbt_analytics_snapshot_schedule,
]
