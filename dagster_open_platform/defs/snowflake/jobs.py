from dagster import Config, In, Nothing, OpExecutionContext, ResourceParam, job, op
from dagster_snowflake import SnowflakeConnection, snowflake_resource


class DatabaseCloneConfig(Config):
    pull_request_id: str


@op
def drop_database_clone(
    config: DatabaseCloneConfig,
    snowflake: ResourceParam[SnowflakeConnection],
):
    """Drops a clone of the Purina Snowflake database associated with a Pull Request,
    based on the pull request id provided in the config.
    """
    snowflake.execute_queries(
        sql_queries=[
            f"CALL UTIL_DB.PUBLIC.CLEANUP_DATABASE_CLONE('PURINA', '{config.pull_request_id}')",
            f"CALL UTIL_DB.PUBLIC.CLEANUP_DATABASE_CLONE('DWH_REPORTING', '{config.pull_request_id}')",
        ],
        fetch_results=True,
    )


@op(ins={"start": In(Nothing)})
def clone_database(
    context: OpExecutionContext,
    config: DatabaseCloneConfig,
    snowflake: ResourceParam[SnowflakeConnection],
):
    """Creates a copy-on-write of the Purina Snowflake database associated with a Pull Request,
    based on the pull request id provided in the config. This process is powered by a stored
    procedure defined in DOP under the procedures/admin directory.
    """
    snowflake.execute_queries(
        sql_queries=[
            f"CALL UTIL_DB.PUBLIC.CLONE_DATABASE('PURINA', '{config.pull_request_id}')",
            f"CALL UTIL_DB.PUBLIC.CLONE_DATABASE('DWH_REPORTING', '{config.pull_request_id}')",
        ],
        fetch_results=True,
    )


@job(
    resource_defs={
        "snowflake": snowflake_resource,
    },
    config={
        "resources": {
            "snowflake": {
                "config": {
                    "account": {"env": "SNOWFLAKE_PURINA_ACCOUNT"},
                    "user": {"env": "SNOWFLAKE_PURINA_USER"},
                    "password": {"env": "SNOWFLAKE_PURINA_PASSWORD"},
                    "database": {"env": "SNOWFLAKE_PURINA_DATABASE"},
                    "schema": {"env": "SNOWFLAKE_PURINA_SCHEMA"},
                }
            }
        },
        "ops": {
            "drop_database_clone": {
                "config": {
                    "pull_request_id": {"env": "DAGSTER_CLOUD_PULL_REQUEST_ID"},
                }
            },
            "clone_database": {
                "config": {
                    "pull_request_id": {"env": "DAGSTER_CLOUD_PULL_REQUEST_ID"},
                }
            },
        },
    },
    description="""Creates a copy-on-write of the Purina Snowflake database associated with a Pull Request.
This is automatically run when a Pull Request is opened via GitHub Action.""",
)
def clone_databases() -> None:
    clone_database(start=drop_database_clone())


@job(
    resource_defs={
        "snowflake": snowflake_resource,
    },
    config={
        "resources": {
            "snowflake": {
                "config": {
                    "account": {"env": "SNOWFLAKE_PURINA_ACCOUNT"},
                    "user": {"env": "SNOWFLAKE_PURINA_USER"},
                    "password": {"env": "SNOWFLAKE_PURINA_PASSWORD"},
                    "database": {"env": "SNOWFLAKE_PURINA_DATABASE"},
                    "schema": {"env": "SNOWFLAKE_PURINA_SCHEMA"},
                }
            }
        },
        "ops": {
            "drop_database_clone": {
                "config": {
                    "pull_request_id": {"env": "DAGSTER_CLOUD_PULL_REQUEST_ID"},
                }
            }
        },
    },
    description="""Drops a clone of the Purina Snowflake database associated with a Pull Request.
This is automatically run when a Pull Request is closed via GitHub Action. The `drop_old_purina_clones`
sensor will also periodically run to clean up any clones that may have been overlooked.
""",
)
def drop_database_clones() -> None:
    drop_database_clone()
