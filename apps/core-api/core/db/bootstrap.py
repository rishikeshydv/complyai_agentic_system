from __future__ import annotations

from core.db.models import Base
from core.db.session import engine


def bootstrap() -> None:
    Base.metadata.create_all(bind=engine)


def main() -> None:
    bootstrap()


if __name__ == "__main__":
    main()
