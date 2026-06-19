from __future__ import annotations

import logging
from pathlib import Path

from dalembic.deployment import DeploymentManager
from dalembic.settings import DeploySettings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    settings = DeploySettings.from_env(repo_root=Path.cwd())
    DeploymentManager(settings).deploy()


if __name__ == "__main__":
    main()
