import re

def smart_chunk(text, target_size=1000, overlap=150, min_chunk=200):
    text = re.sub(r'\n{3,}', '\n\n', text)
    paragraphs = re.split(r'\n\s*\n', text)

    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) <= target_size:
            current += ("\n\n" if current else "") + para
        else:
            if len(current) >= min_chunk:
                chunks.append(current)
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + "\n\n" + para
            else:
                current += ("\n\n" if current else "") + para

            while len(current) > target_size * 1.5:
                chunks.append(current[:target_size])
                current = current[target_size - overlap:]

    if current.strip() and len(current.strip()) >= min_chunk:
        chunks.append(current.strip())

    return chunks
