"""
Persist uploaded media in Postgres so images survive Render free-tier redeploys
(ephemeral disk loses /media files on every deploy).
"""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def persist_media_blob(field_file):
    """Save ImageField/FileField bytes into MediaBlob keyed by storage path."""
    if not field_file or not getattr(field_file, 'name', None):
        return

    from .models import MediaBlob

    name = field_file.name.replace('\\', '/').lstrip('/')
    data = None

    # Prefer reading the in-memory / just-uploaded file
    try:
        field_file.open('rb')
        data = field_file.read()
        field_file.close()
    except Exception:
        data = None

    # Fallback: read from disk under MEDIA_ROOT
    if not data:
        disk = Path(settings.MEDIA_ROOT) / name
        if disk.is_file():
            data = disk.read_bytes()

    if not data:
        return

    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    MediaBlob.objects.update_or_create(
        path=name,
        defaults={
            'data': data,
            'content_type': content_type,
            'size': len(data),
        },
    )


def restore_blob_to_disk(path):
    """Write MediaBlob back to MEDIA_ROOT if missing (optional helper)."""
    from .models import MediaBlob

    path = path.replace('\\', '/').lstrip('/')
    disk = Path(settings.MEDIA_ROOT) / path
    if disk.is_file():
        return disk
    try:
        blob = MediaBlob.objects.get(path=path)
    except MediaBlob.DoesNotExist:
        return None
    disk.parent.mkdir(parents=True, exist_ok=True)
    disk.write_bytes(bytes(blob.data))
    return disk


def serve_media(request, path):
    """
    Serve /media/<path>:
    1) file on disk (MEDIA_ROOT)
    2) MediaBlob row in database
    """
    path = (path or '').replace('\\', '/').lstrip('/')
    if not path or '..' in path.split('/'):
        raise Http404('Invalid path')

    disk = Path(settings.MEDIA_ROOT) / path
    if disk.is_file():
        content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        resp = FileResponse(open(disk, 'rb'), content_type=content_type)
        resp['Cache-Control'] = 'public, max-age=86400'
        return resp

    from .models import MediaBlob

    blob = MediaBlob.objects.filter(path=path).first()
    if not blob:
        # sometimes name stored without folder quirks
        blob = MediaBlob.objects.filter(path__endswith=path.split('/')[-1]).first()

    if blob and blob.data:
        resp = HttpResponse(bytes(blob.data), content_type=blob.content_type or 'application/octet-stream')
        resp['Cache-Control'] = 'public, max-age=86400'
        resp['Content-Length'] = str(blob.size or len(blob.data))
        return resp

    raise Http404('Media not found')


def sync_media_dir_to_db(root=None):
    """Import every file under MEDIA_ROOT into MediaBlob (used at build time)."""
    from .models import MediaBlob

    root = Path(root or settings.MEDIA_ROOT)
    if not root.is_dir():
        return 0

    count = 0
    for file_path in root.rglob('*'):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root).as_posix()
        data = file_path.read_bytes()
        content_type = mimetypes.guess_type(rel)[0] or 'application/octet-stream'
        MediaBlob.objects.update_or_create(
            path=rel,
            defaults={
                'data': data,
                'content_type': content_type,
                'size': len(data),
            },
        )
        count += 1
    return count
