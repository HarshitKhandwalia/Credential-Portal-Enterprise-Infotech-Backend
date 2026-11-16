import json
import re
from io import BytesIO

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

REQUIRED_SETTINGS = (
    'CLOUDINARY_CLOUD_NAME',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET',
)

_configured = False


class CloudinaryUploadError(RuntimeError):
    """Raised when a Cloudinary upload fails."""


def _validate_settings():
    missing = [
        name
        for name in REQUIRED_SETTINGS
        if not getattr(settings, name, None)
    ]
    if missing:
        raise ImproperlyConfigured(
            'Cloudinary is not configured. Set the following environment '
            'variables: ' + ', '.join(missing)
        )


def configure_cloudinary():
    """Configure the Cloudinary SDK from Django settings (idempotent)."""
    global _configured
    if _configured:
        return
    _validate_settings()
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    _configured = True


def sanitize_template_folder_name(template_name):
    """
    Turn a template name into a Cloudinary-safe folder segment.
    e.g. \"Default Pass!\" -> \"default-pass\"
    """
    if not template_name or not str(template_name).strip():
        raise CloudinaryUploadError('template_name is required.')

    slug = str(template_name).strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    if not slug:
        raise CloudinaryUploadError('template_name must contain letters or numbers.')
    return slug[:100]


def template_folder_path(template_name):
    """Return ``{base_folder}/{sanitized_template_name}``."""
    base = (settings.CLOUDINARY_UPLOAD_FOLDER or 'templates').strip('/')
    slug = sanitize_template_folder_name(template_name)
    return f'{base}/{slug}' if base else slug


def upload_image(file, *, template_name, asset_name=None):
    """
    Upload an image into the template's Cloudinary folder.

    ``asset_name`` (e.g. icon, strip, logo, heroImage) becomes a stable public_id
    inside that folder so re-uploads overwrite the same asset.
    """
    configure_cloudinary()
    folder = template_folder_path(template_name)
    options = {
        'folder': folder,
        'resource_type': 'image',
    }
    if asset_name:
        safe_asset = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(asset_name).strip())
        if safe_asset:
            options['public_id'] = safe_asset
            options['overwrite'] = True
            options['invalidate'] = True

    try:
        result = cloudinary.uploader.upload(file, **options)
    except Exception as exc:
        raise CloudinaryUploadError(str(exc)) from exc

    url = result.get('secure_url') or result.get('url')
    if not url:
        raise CloudinaryUploadError('Cloudinary response did not include a URL.')

    return {
        'url': url,
        'public_id': result.get('public_id'),
        'resource_type': result.get('resource_type', 'image'),
        'folder': folder,
    }


def upload_template_data(template_name, data):
    """
    Upload/overwrite ``template.json`` in the template's Cloudinary folder.
    Stores the template payload alongside its image assets.
    """
    configure_cloudinary()
    folder = template_folder_path(template_name)
    payload = json.dumps(data, indent=2, default=str).encode('utf-8')
    buffer = BytesIO(payload)
    buffer.name = 'template.json'

    try:
        result = cloudinary.uploader.upload(
            buffer,
            folder=folder,
            public_id='template',
            resource_type='raw',
            format='json',
            overwrite=True,
            invalidate=True,
        )
    except Exception as exc:
        raise CloudinaryUploadError(str(exc)) from exc

    url = result.get('secure_url') or result.get('url')
    if not url:
        raise CloudinaryUploadError('Cloudinary response did not include a URL.')

    return {
        'url': url,
        'public_id': result.get('public_id'),
        'resource_type': result.get('resource_type', 'raw'),
        'folder': folder,
    }
