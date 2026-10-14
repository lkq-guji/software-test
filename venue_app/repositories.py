"""可替换的 JSON/内存 Repository；只处理数据存取，不做业务判断。"""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Generic, Iterable, Protocol, TypeVar

from .errors import DomainError
from .models import Booking, User, Venue

Entity = TypeVar("Entity", User, Venue, Booking)


class Repository(Protocol[Entity]):
    """业务层使用的仓库协议。"""

    def list_all(self) -> list[Entity]:
        """返回全部记录的独立列表。"""
        ...

    def get(self, record_id: str) -> Entity | None:
        """按主键查询，不存在时返回 None。"""
        ...

    def add(self, entity: Entity) -> None:
        """新增记录；重复主键抛出 DomainError。"""
        ...

    def update(self, entity: Entity) -> None:
        """替换已有记录；缺失主键抛出 DomainError。"""
        ...


class MemoryRepository(Generic[Entity]):
    """按主键存储冻结模型的内存仓库，用于隔离测试。"""

    def __init__(self, key_field: str, initial: Iterable[Entity] = ()) -> None:
        """从初始记录构造仓库，并检查主键重复。"""
        self.key_field = key_field
        self._records: dict[str, Entity] = {}
        for entity in initial:
            self.add(entity)

    def list_all(self) -> list[Entity]:
        """返回全部记录的新列表。"""
        return list(self._records.values())

    def get(self, record_id: str) -> Entity | None:
        """按主键查找记录。"""
        return self._records.get(record_id)

    def add(self, entity: Entity) -> None:
        """新增实体；拒绝重复主键。"""
        record_id = getattr(entity, self.key_field)
        if record_id in self._records:
            raise DomainError("E_DUPLICATE_ID")
        self._records[record_id] = entity

    def update(self, entity: Entity) -> None:
        """显式替换实体；不隐式创建记录。"""
        record_id = getattr(entity, self.key_field)
        if record_id not in self._records:
            raise DomainError("E_RECORD_NOT_FOUND")
        self._records[record_id] = entity


class JsonRepository(Generic[Entity]):
    """UTF-8 JSON 仓库；保存采用同目录临时文件加原子替换。"""

    def __init__(self, path: str | Path, model: type[Entity], key_field: str) -> None:
        """配置文件路径、模型构造器和主键，不改写已有文件。"""
        self.path = Path(path)
        self.model = model
        self.key_field = key_field

    def list_all(self) -> list[Entity]:
        """读取数组并构造模型；损坏文件返回错误而非当作空数据。"""
        try:
            with self.path.open("r", encoding="utf-8-sig") as stream:
                payload = json.load(stream)
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, UnicodeError):
            raise DomainError("E_REPOSITORY_FORMAT") from None

        except OSError:
            raise DomainError("E_REPOSITORY_IO") from None
        if not isinstance(payload, list):
            raise DomainError("E_REPOSITORY_FORMAT")
        try:
            entities = [self.model(**record) for record in payload]
            keys = [getattr(entity, self.key_field) for entity in entities]
            if any(not isinstance(key, str) for key in keys) or len(set(keys)) != len(keys):
                raise DomainError("E_REPOSITORY_FORMAT")
            return entities
        except (TypeError, KeyError, ValueError):
            raise DomainError("E_REPOSITORY_FORMAT") from None

    def initialize(self, initial: Iterable[Entity] = ()) -> None:
        """仅在文件缺失时保存初始数据，已有文件（含损坏文件）不覆盖。"""
        if not self.path.exists():
            self._write(list(initial))

    def get(self, record_id: str) -> Entity | None:
        """从最新文件内容查找主键。"""
        return next((entity for entity in self.list_all()
                     if getattr(entity, self.key_field) == record_id), None)

    def add(self, entity: Entity) -> None:
        """读取后追加并保存，拒绝重复主键。"""
        records = self.list_all()
        record_id = getattr(entity, self.key_field)
        if any(getattr(item, self.key_field) == record_id for item in records):
            raise DomainError("E_DUPLICATE_ID")
        self._write([*records, entity])

    def update(self, entity: Entity) -> None:
        """替换已有主键并保存，缺失主键时拒绝。"""
        records = self.list_all()
        record_id = getattr(entity, self.key_field)
        for index, current in enumerate(records):
            if getattr(current, self.key_field) == record_id:
                records[index] = entity
                self._write(records)
                return
        raise DomainError("E_RECORD_NOT_FOUND")

    def _write(self, records: list[Entity]) -> None:
        temporary: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps([asdict(record) for record in records],
                                    ensure_ascii=False, indent=2, allow_nan=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=self.path.parent, delete=False,
                                             suffix=".tmp") as stream:
                temporary = Path(stream.name)
                stream.write(serialized + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except (TypeError, ValueError):
            raise DomainError("E_REPOSITORY_FORMAT") from None
        except OSError:
            raise DomainError("E_REPOSITORY_IO") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def json_repositories(data_dir: str | Path) -> tuple[
    JsonRepository[User], JsonRepository[Venue], JsonRepository[Booking]
]:
    """从数据目录构造用户、场馆和预约仓库。"""
    folder = Path(data_dir)
    return (JsonRepository(folder / "users.json", User, "user_id"),
            JsonRepository(folder / "venues.json", Venue, "venue_id"),
            JsonRepository(folder / "bookings.json", Booking, "booking_id"))
