from app.services.rag.citations import cited_snippet_indexes, filter_authorized_to_cited


def test_cited_snippet_indexes_are_unique_and_ordered():
    text = "Hours are 09:00 [1]. The same file also lists Friday [1] and a contact [3]."
    assert cited_snippet_indexes(text) == [1, 3]


def test_filter_skips_out_of_range_and_unused_chunks():
    authorized = [
        {"filename": "matara.pdf", "content": "Matara hours"},
        {"filename": "revenue.csv", "content": "Revenue"},
        {"filename": "complaints.xlsx", "content": "Complaints"},
    ]
    answer = "The Matara branch operates 09:00–16:30 [1]."
    selected = filter_authorized_to_cited(authorized, answer)
    assert [(index, item["filename"]) for index, item in selected] == [(1, "matara.pdf")]


def test_filter_keeps_multiple_citations_in_answer_order():
    authorized = [
        {"filename": "a.pdf"},
        {"filename": "b.pdf"},
        {"filename": "c.pdf"},
    ]
    selected = filter_authorized_to_cited(authorized, "See [3] then [1].")
    assert [index for index, _ in selected] == [3, 1]


def test_filter_ignores_trailing_unused_bibliography():
    authorized = [
        {"filename": "Matara Branch Information.pdf"},
        {"filename": "Revenue Report.csv"},
        {"filename": "Complaints.xlsx"},
    ]
    answer = (
        "The Matara branch operates from Monday to Friday, from 9:00 AM to 4:30 PM [1].\n\n"
        "Sources:\n"
        "[1] Matara Branch Information.pdf\n"
        "[2] Revenue Report.csv\n"
        "[3] Complaints.xlsx"
    )
    selected = filter_authorized_to_cited(authorized, answer)
    assert [(index, item["filename"]) for index, item in selected] == [
        (1, "Matara Branch Information.pdf")
    ]


def test_filter_supports_comma_list_and_duplicates():
    authorized = [{"filename": "a.pdf"}, {"filename": "b.pdf"}, {"filename": "c.pdf"}]
    selected = filter_authorized_to_cited(authorized, "Hours [1, 3] and again [1].")
    assert [index for index, _ in selected] == [1, 3]
