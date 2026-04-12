"""
API Documents - Explorador de documentos del NAS
"""

from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, send_file

documents_bp = Blueprint("api_documents", __name__)

ALLOWED_EXTENSIONS = ["*.pdf", "*.jpg", "*.jpeg", "*.png", "*.txt", "*.webp", "*.heic", "*.heif"]
ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
}


@documents_bp.route("/api/docs/structure")
def api_docs_structure():
    """
    Estructura de carpetas y archivos del NAS.
    Salida: {"Categoria": [{"name": ..., "path": ...}, ...]}
    """
    docs_path = current_app.config.get("DOCS_BASE_PATH")

    if not docs_path:
        current_app.logger.error("DOCS_BASE_PATH no está definido en config.py o .env")
        return jsonify({"error": "Configuración incompleta: DOCS_BASE_PATH no definido"}), 500

    base = Path(docs_path)

    if not base.exists():
        current_app.logger.error(f"Ruta NAS no encontrada: {docs_path}")
        return jsonify({
            "error": f"No se puede acceder a la carpeta de documentos ({docs_path}). "
                     "Verifica el volumen en Docker.",
        }), 404

    structure = {}

    try:
        for folder in sorted(base.iterdir()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue

            folder_name = folder.name
            file_list = []

            for ext in ALLOWED_EXTENSIONS:
                for file in sorted(folder.rglob(ext)):
                    relative_path = file.relative_to(folder).as_posix()
                    path_parts = file.relative_to(folder).parts
                    if any(part.startswith(".") or part.startswith("@") for part in path_parts):
                        continue

                    file_list.append({
                        "name": relative_path.rsplit(".", 1)[0],
                        "filename": file.name,
                        "type": file.suffix.lower(),
                        "path": f"/docs/{folder_name}/{relative_path}",
                    })

            if file_list:
                structure[folder_name] = file_list

        return jsonify(structure)

    except PermissionError:
        current_app.logger.error(f"Permiso denegado al leer el NAS en: {base}")
        return jsonify({
            "error": "Permiso denegado. Revisa permisos de lectura en el volumen Docker",
        }), 403

    except Exception as e:
        current_app.logger.error(f"Error general leyendo estructura NAS: {e}")
        return jsonify({"error": "Error interno leyendo documentos"}), 500


@documents_bp.route("/docs/<categoria>/<path:filename>")
def serve_document(categoria, filename):
    """Sirve archivos desde el NAS."""
    docs_base_str = current_app.config.get("DOCS_BASE_PATH")
    if not docs_base_str:
        abort(500, description="DOCS_BASE_PATH no configurado")

    base_path = Path(docs_base_str).resolve()

    try:
        file_path = (base_path / categoria / filename).resolve()
    except Exception:
        abort(404)

    # Path Traversal protection
    if base_path not in file_path.parents:
        abort(403)

    if file_path.suffix.lower() not in ALLOWED_SUFFIXES:
        abort(403)

    if not file_path.exists() or not file_path.is_file():
        abort(404)

    mimetype = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=file_path.name,
    )
