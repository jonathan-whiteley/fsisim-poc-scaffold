"""Idempotent creation of catalog, schema, and managed volume in DEFAULT workspace."""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType
from config import Config


def main() -> None:
    cfg = Config()
    w = WorkspaceClient()

    print(f"Ensuring catalog {cfg.catalog} ...")
    existing = {c.name for c in w.catalogs.list()}
    if cfg.catalog not in existing:
        w.catalogs.create(name=cfg.catalog, comment="FSISIM POC scaffold (mock data)")
        print(f"  created catalog {cfg.catalog}")
    else:
        print(f"  catalog {cfg.catalog} already exists")

    print(f"Ensuring schema {cfg.catalog}.{cfg.schema} ...")
    existing_schemas = {s.name for s in w.schemas.list(catalog_name=cfg.catalog)}
    if cfg.schema not in existing_schemas:
        w.schemas.create(
            name=cfg.schema,
            catalog_name=cfg.catalog,
            comment="FSISIM gold-tier issues + manuals (mock)",
        )
        print(f"  created schema {cfg.schema}")
    else:
        print(f"  schema {cfg.schema} already exists")

    print(f"Ensuring volume {cfg.manuals_volume_path} ...")
    existing_vols = {
        v.name for v in w.volumes.list(catalog_name=cfg.catalog, schema_name=cfg.schema)
    }
    if cfg.volume_name not in existing_vols:
        w.volumes.create(
            catalog_name=cfg.catalog,
            schema_name=cfg.schema,
            name=cfg.volume_name,
            volume_type=VolumeType.MANAGED,
        )
        print(f"  created volume {cfg.volume_name}")
    else:
        print(f"  volume {cfg.volume_name} already exists")

    print("Done.")


if __name__ == "__main__":
    main()
