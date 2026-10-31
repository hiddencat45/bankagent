def test_assistant_space_real_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from scripts.capture_assistant_space import run
    report = run(tmp_path, width=1040, height=720)
    assert report['after_minor'] == 497000
