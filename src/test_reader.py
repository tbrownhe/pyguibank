from core.validation import PDFReader
from pathlib import Path

table_settings = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "text",
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": [],
    "snap_tolerance": 3,
    "snap_x_tolerance": 3,
    "snap_y_tolerance": 3,
    "join_tolerance": 3,
    "join_x_tolerance": 3,
    "join_y_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 3,
    "min_words_horizontal": 1,
    "intersection_tolerance": 3,
    "intersection_x_tolerance": 3,
    "intersection_y_tolerance": 3,
    "text_tolerance": 3,
    "text_x_tolerance": 3,
    "text_y_tolerance": 3,
}

fpath = Path(r"g:\My Drive\Banking\Import\SUCCESS\CITIAA_20201204_20210105.pdf")
with PDFReader(fpath) as reader:
    for page in reader.doc.pages:
        print(page)
        for table in page.extract_tables(table_settings=table_settings):
            for row in table:
                print(row)
