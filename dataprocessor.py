from pathlib import Path

from pdfreader import read_pdf
from chunker import chunk_pages
from embedder import embed_chunks
from vectorstore import store_chunks

PDF_DIR = Path("./resources")


def run():
    # Process every PDF in ./resources (the assignment has several SOPs and manuals)
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        # Read the PDF and extract text
        pages = read_pdf(str(pdf_path))

        # Chunk the extracted text into manageable pieces
        chunks = chunk_pages(pages, chunk_size=1100, chunk_overlap=180)

        # Embed with the local Ollama model, then store
        embedded_chunks = embed_chunks(chunks)
        store_chunks(chunks, embedded_chunks, source=pdf_path.name)

        print(f"{pdf_path.name}: {len(chunks)} chunks stored")


if __name__ == "__main__":
    run()
