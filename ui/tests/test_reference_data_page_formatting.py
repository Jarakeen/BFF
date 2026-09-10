from ui.reference_data_page import _reference_details_html


def test_reference_detail_labels_render_bold_without_bolding_values():
    rendered = _reference_details_html(
        (
            ("Requires movement", "Yes"),
            ("Evidence • Target pattern", "Three sequential meteors"),
        )
    )

    assert "<b>Requires movement:</b> Yes" in rendered
    assert "<b>Evidence • Target pattern:</b> Three sequential meteors" in rendered
    assert "<b>Yes</b>" not in rendered


def test_reference_detail_html_escapes_source_text():
    rendered = _reference_details_html((("Rule <type>", "A & B"),))

    assert "<b>Rule &lt;type&gt;:</b> A &amp; B" in rendered
