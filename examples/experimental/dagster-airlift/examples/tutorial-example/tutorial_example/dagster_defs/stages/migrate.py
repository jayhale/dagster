import os
from pathlib import Path

from dagster import AssetSpec, Definitions, multi_asset
from dagster._core.definitions.materialize import materialize
from dagster_airlift.core import (
    AirflowInstance,
    BasicAuthBackend,
    build_defs_from_airflow_instance,
    dag_defs,
    task_defs,
)
from dagster_airlift.dbt import dbt_defs
from dagster_dbt import DbtProject

# Code also invoked from Airflow
from tutorial_example.shared.export_duckdb_to_csv import ExportDuckDbToCsvArgs, export_duckdb_to_csv
from tutorial_example.shared.load_csv_to_duckdb import LoadCsvToDuckDbArgs, load_csv_to_duckdb


def dbt_project_path() -> Path:
    env_val = os.getenv("TUTORIAL_DBT_PROJECT_DIR")
    assert env_val, "TUTORIAL_DBT_PROJECT_DIR must be set"
    return Path(env_val)


def airflow_dags_path() -> Path:
    return Path(__file__).parent / "tutorial_example" / "airflow_dags"


def load_csv_to_duckdb_defs(args: LoadCsvToDuckDbArgs) -> Definitions:
    spec = AssetSpec(key=[args.duckdb_schema, args.table_name])

    @multi_asset(name=f"load_{args.table_name}", specs=[spec])
    def _multi_asset() -> None:
        load_csv_to_duckdb(args)

    return Definitions(assets=[_multi_asset])


def export_duckdb_to_csv_defs(args: ExportDuckDbToCsvArgs) -> Definitions:
    spec = AssetSpec(
        key=str(args.csv_path).rsplit("/", 2)[-1].replace(".", "_"), deps=[args.table_name]
    )

    @multi_asset(name=f"export_{args.table_name}", specs=[spec])
    def _multi_asset() -> None:
        export_duckdb_to_csv(args)

    return Definitions(assets=[_multi_asset])


defs = build_defs_from_airflow_instance(
    airflow_instance=AirflowInstance(
        auth_backend=BasicAuthBackend(
            webserver_url="http://localhost:8080",
            username="admin",
            password="admin",
        ),
        name="airflow_instance_one",
    ),
    defs=dag_defs(
        "rebuild_customers_list",
        task_defs(
            "load_raw_customers",
            load_csv_to_duckdb_defs(
                LoadCsvToDuckDbArgs(
                    table_name="raw_customers",
                    csv_path=airflow_dags_path() / "raw_customers.csv",
                    duckdb_path=Path(os.environ["AIRFLOW_HOME"]) / "jaffle_shop.duckdb",
                    names=["id", "first_name", "last_name"],
                    duckdb_schema="raw_data",
                    duckdb_database_name="jaffle_shop",
                )
            ),
        ),
        task_defs(
            "build_dbt_models",
            # load rich set of assets from dbt project
            dbt_defs(
                manifest=dbt_project_path() / "target" / "manifest.json",
                project=DbtProject(str(dbt_project_path().absolute())),
            ),
        ),
        task_defs(
            "export_customers",
            export_duckdb_to_csv_defs(
                ExportDuckDbToCsvArgs(
                    table_name="customers",
                    # TODO use env var?
                    csv_path=airflow_dags_path() / "customers.csv",
                    duckdb_path=Path(os.environ["AIRFLOW_HOME"]) / "jaffle_shop.duckdb",
                    duckdb_schema="raw_data",
                    duckdb_database_name="jaffle_shop",
                )
            ),
        ),
    ),
)


if __name__ == "__main__":
    assert dbt_project_path().exists()
    # print(dbt_project_path().absolute())
    Definitions.validate_loadable(defs)
    materialize(defs.get_asset_graph().assets_defs)
