import mimetypes
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from vercel.blob import sync as blob
from vercel.blob.errors import BlobNotFoundError


class VercelBlobStorage(Storage):
    """Public image storage. SDK reads BLOB_READ_WRITE_TOKEN from the environment."""

    def _save(self, name, content):
        result = blob.put_blob(name, content.read(), access='public',
            content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream',
            add_random_suffix=False, allow_overwrite=False)
        return result.pathname

    def _open(self, name, mode='rb'):
        if mode not in ('r', 'rb'):
            raise ValueError('Blob files are read-only; save a new file instead.')
        return ContentFile(blob.get_blob(name, access='public').body, name=name)

    def exists(self, name):
        try:
            blob.head_blob(name)
            return True
        except BlobNotFoundError:
            return False

    def url(self, name):
        if not name:
            return ''
        try:
            return blob.head_blob(name).url
        except BlobNotFoundError:
            return ''

    def size(self, name):
        return blob.head_blob(name).size

    def delete(self, name):
        if name and self.exists(name):
            blob.delete_blob(name)
