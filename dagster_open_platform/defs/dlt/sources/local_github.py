"""Local invocation of GitHub issues pipeline.

USAGE

    python -m dagster_open_platform.dlt.sources.local_github


"""

import os

import yaml
from dagster_open_platform.defs.dlt.sources.github import github_reactions
from dlt import pipeline

if __name__ == "__main__":
    cwd = os.path.dirname(os.path.abspath(__file__))
    dlt_configuration_path = os.path.join(cwd, "configuration.yaml")
    dlt_configuration = yaml.safe_load(open(dlt_configuration_path))

    dlt_source = github_reactions(
        dlt_configuration["sources"]["github"]["repositories"],
        items_per_page=100,
        max_items=1000,
    )

    dlt_pipeline = pipeline(
        pipeline_name="github_issues",
        dataset_name="github",
        destination="snowflake",
    )

    dlt_pipeline.run(dlt_source)
