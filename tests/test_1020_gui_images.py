import pytest
import sys
import subprocess
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shinestacker.gui.gui_images import GuiPdfView, GuiImageView, open_file


@pytest.fixture
def app(qtbot):
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    app.quit()


@pytest.fixture
def sample_image(tmp_path):
    img_path = tmp_path / "test_image.png"
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.red)
    pixmap.save(str(img_path))
    return str(img_path)


@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_content = b'''%PDF-1.1
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 100 100] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000114 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
164
%%EOF'''
    with open(pdf_path, 'wb') as f:
        f.write(pdf_content)
    return str(pdf_path)


def _patch_open(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, args, *a, **kw):
            calls.append(args)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(subprocess, 'Popen', FakePopen)
    monkeypatch.setattr('os.startfile', lambda *a, **k: calls.append(a), raising=False)
    monkeypatch.setattr('webbrowser.open', lambda *a, **k: calls.append(a), raising=False)
    return calls


def test_open_file_image(sample_image, qtbot, monkeypatch):
    calls = _patch_open(monkeypatch)
    open_file(sample_image)
    assert len(calls) >= 1


def test_gui_image_view_click(sample_image, qtbot, monkeypatch):
    calls = _patch_open(monkeypatch)
    image_view = GuiImageView(sample_image)
    qtbot.addWidget(image_view)
    QTest.mouseDClick(image_view, Qt.LeftButton)
    assert len(calls) >= 1


def test_gui_pdf_view_click(sample_pdf, qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(
        'shinestacker.gui.gui_images.open_file',
        lambda path, *a, **k: calls.append(path),
    )
    pdf_view = GuiPdfView(sample_pdf)
    qtbot.addWidget(pdf_view)

    class MockEvent:
        def button(self):
            return Qt.LeftButton

    pdf_view.mouseDoubleClickEvent(MockEvent())
    assert calls == [sample_pdf]
