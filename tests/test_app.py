from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_lab_verifies_and_clears_stale_results():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=60)
    assert not app.exception
    verify = next(button for button in app.button if button.label == 'Verify with biochemical solver')
    verify.click().run(timeout=60)
    assert not app.exception
    assert len(app.success) == 1
    curve = next(button for button in app.button if button.label == 'Calculate the trade-off curve')
    curve.click().run(timeout=60)
    assert not app.exception
    assert len(app.session_state['envelope']) == 15
    app.sidebar.select_slider[0].set_value(6).run(timeout=60)
    assert not app.exception
    assert 'verification' not in app.session_state
    assert 'envelope' not in app.session_state
