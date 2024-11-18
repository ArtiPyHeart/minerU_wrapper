import os
import subprocess
import tempfile
import traceback
import uuid
from io import BytesIO
from pathlib import Path

import requests
from docx import Document
from flask import Flask, jsonify, request
from loguru import logger
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter

app = Flask(__name__)


def _read_file_from_path_or_url(url_or_path) -> BytesIO:
    if url_or_path.startswith("http"):
        response = requests.get(
            url_or_path,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        )
        response.raise_for_status()
        return BytesIO(response.content)
    else:
        path = Path(url_or_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "rb") as file:
            return BytesIO(file.read())


def _create_temp_file(bytes_io, suffix) -> Path:
    temp_dir = tempfile.TemporaryDirectory()
    temp_file = Path(temp_dir.name) / f"{uuid.uuid4()}.{suffix}"
    with open(temp_file, "wb") as file:
        file.write(bytes_io.getvalue())
    return temp_file


def convert_pdf_to_markdown(pdf_path: str) -> str:
    bytes_io = _read_file_from_path_or_url(pdf_path)
    pdf_bytes = bytes_io.read()
    with tempfile.TemporaryDirectory() as temp_dir:
        image_writer = DiskReaderWriter(Path(temp_dir) / "images")
        json_useful_key = {"_pdf_type": "", "model_list": []}
        pipe = UNIPipe(pdf_bytes, json_useful_key, image_writer)
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        content_list: list[dict] = pipe.pipe_mk_uni_format(temp_dir, drop_mode="none")

        markdown_content = ""
        for item in content_list:
            if item["type"] == "text":
                markdown_content += item["text"] + "\n\n"
        return markdown_content


def convert_docx_to_markdown(url_or_path: str) -> str:
    bytes_io = _read_file_from_path_or_url(url_or_path)

    if url_or_path.endswith(".doc") or url_or_path.endswith(".wps"):
        suffix = url_or_path.split(".")[-1]
        temp_dir = tempfile.TemporaryDirectory()
        temp_file = Path(temp_dir.name) / f"{uuid.uuid4()}.{suffix}"
        with open(temp_file, "wb") as file:
            file.write(bytes_io.getvalue())
        doc_path = temp_file
        output_dir = os.path.dirname(doc_path)
        command = [
            "soffice",
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            output_dir,
            doc_path,
        ]
        subprocess.call(command)
        url_or_path = os.path.splitext(doc_path)[0] + ".docx"
        bytes_io = _read_file_from_path_or_url(url_or_path)

    if url_or_path.endswith(".docx"):
        document = Document(bytes_io)
        final_res = ""
        for paragraph in document.paragraphs:
            final_res += paragraph.text + "\n"
        return final_res
    else:
        raise ValueError(f"Unsupported file type: {url_or_path}")


@app.route("/convert", methods=["POST"])
def convert_endpoint():
    try:
        data = request.get_json()
        if not data or "path" not in data:
            return jsonify({"error": "Missing path in request"}), 400

        raw_path = data["path"]
        if raw_path.endswith(".pdf"):
            markdown_text = convert_pdf_to_markdown(raw_path)
        else:
            markdown_text = convert_docx_to_markdown(raw_path)
        return jsonify({"markdown": markdown_text})

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9999)
