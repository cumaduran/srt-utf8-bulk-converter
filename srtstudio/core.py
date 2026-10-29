"""Encoding-safe, dependency-free SRT discovery and conversion engine."""

from __future__ import annotations

import codecs
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Options:
    sources: tuple[Path, ...]
    output_directory: Path | None = None  # None = <source folder>/utf8
    recursive: bool = True
    preserve_structure: bool = True
    overwrite: bool = False


@dataclass(frozen=True)
class Job:
    source: Path
    destination: Path
    conflict: str = ""


@dataclass(frozen=True)
class Result:
    source: Path
    destination: Path
    status: str  # done | warning | skipped | failed
    encoding: str
    message: str


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _srt_files(folder: Path, recursive: bool, excluded: set[Path]) -> Iterable[Path]:
    if not recursive:
        for path in sorted(folder.iterdir(), key=lambda p: str(p).casefold()):
            if path.is_file() and path.suffix.casefold() == '.srt' and not any(_is_inside(path.resolve(), ex) for ex in excluded):
                yield path.resolve()
        return

    for base, dirs, files in os.walk(folder, followlinks=False):
        base_path = Path(base)
        dirs[:] = sorted(
            (name for name in dirs
             if name.casefold() != 'utf8'
             and not any(_is_inside((base_path / name).resolve(), ex) for ex in excluded)),
            key=str.casefold,
        )
        for name in sorted(files, key=str.casefold):
            path = (base_path / name).resolve()
            if path.suffix.casefold() == '.srt' and path.is_file() and not any(
                _is_inside(path, ex) for ex in excluded
            ):
                yield path


def build_plan(options: Options) -> list[Job]:
    """Build predictable destinations, avoid converted-output recursion and duplicates."""
    if not options.sources:
        return []
    sources = list(dict.fromkeys(Path(p).expanduser().resolve() for p in options.sources))
    roots = [p for p in sources if p.is_dir()]
    custom = options.output_directory.expanduser().resolve() if options.output_directory else None
    exclusion_roots = {custom} if custom else set()
    # Do not read our own automatic output if it already exists.
    exclusion_roots.update(root / 'utf8' for root in roots)
    multiple_folders = len(roots) > 1
    seen: set[Path] = set()
    allocated: set[str] = set()
    jobs: list[Job] = []

    for selected in sources:
        if selected.is_dir():
            files = _srt_files(selected, options.recursive, exclusion_roots)
        elif selected.is_file() and selected.suffix.casefold() == '.srt':
            files = (selected,)
        else:
            continue

        for path in files:
            if path in seen:
                continue
            seen.add(path)
            if selected.is_dir():
                relative = path.relative_to(selected) if options.preserve_structure else Path(path.name)
                if custom:
                    # Multiple source folders get namespaces to avoid filename collisions.
                    target = custom / selected.name / relative if multiple_folders else custom / relative
                else:
                    target = selected / 'utf8' / relative
            elif custom:
                target = custom / path.name
            else:
                target = path.parent / 'utf8' / path.name
            target = target.resolve()
            conflict = ''
            key = str(target).casefold()  # Windows paths are case insensitive.
            if key in allocated:
                conflict = 'Çıktı adı çakışıyor; dosya atlandı.'
            elif target == path:
                conflict = 'Kaynak ve hedef aynı olamaz.'
            allocated.add(key)
            jobs.append(Job(path, target, conflict))
    return jobs


def decode_subtitle(data: bytes) -> tuple[str, str]:
    """Detect Unicode first; decode legacy Turkish text strictly as Windows-1254."""
    if data.startswith(codecs.BOM_UTF8):
        return data.decode('utf-8-sig'), 'UTF-8 BOM'
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode('utf-16'), 'UTF-16 BOM'
    if b'\x00' in data:
        raise UnicodeError('BOM içermeyen UTF-16 veya ikili içerik; otomatik dönüşüm güvenli değil.')
    try:
        return data.decode('utf-8'), 'UTF-8'
    except UnicodeDecodeError:
        try:
            return data.decode('cp1254'), 'Windows-1254'
        except UnicodeDecodeError as exc:
            raise UnicodeError('UTF-8 ve Windows-1254 olarak okunamadı.') from exc


def convert_one(job: Job, *, overwrite: bool = False) -> Result:
    if job.conflict:
        return Result(job.source, job.destination, 'skipped', '—', job.conflict)
    if job.destination.exists() and not overwrite:
        return Result(job.source, job.destination, 'skipped', '—', 'Hedefte zaten mevcut; üzerine yazılmadı.')
    temp_path: Path | None = None
    try:
        data = job.source.read_bytes()
        content, encoding = decode_subtitle(data)
        if '\ufffd' in content:
            warning = 'İçerikte � karakteri var; daha önce bozulmuş metin otomatik onarılamaz.'
            status = 'warning'
        else:
            warning = f'{encoding} → UTF-8 (BOM yok)'
            status = 'done'
        result_data = content.encode('utf-8')
        job.destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode='wb', prefix='.srtstudio-', suffix='.tmp',
            dir=job.destination.parent, delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(result_data)
        # The guard above prevents ordinary accidental overwrites.
        if job.destination.exists() and not overwrite:
            return Result(job.source, job.destination, 'skipped', encoding, 'Hedef işlem sırasında oluştu.')
        os.replace(temp_path, job.destination)
        temp_path = None
        return Result(job.source, job.destination, status, encoding, warning)
    except (OSError, UnicodeError, ValueError) as exc:
        return Result(job.source, job.destination, 'failed', '—', str(exc))
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def convert_batch(
    options: Options,
    on_result: Callable[[Result, int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[Result]:
    jobs = build_plan(options)
    results: list[Result] = []
    for index, job in enumerate(jobs, 1):
        if should_cancel and should_cancel():
            break
        result = convert_one(job, overwrite=options.overwrite)
        results.append(result)
        if on_result:
            on_result(result, index, len(jobs))
    return results
