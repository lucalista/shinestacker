import pytest
import sys
import platform
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from shinestacker.gui.gui_images import GuiPdfView, GuiImageView, GuiOpenApp, open_file


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


def test_open_file_image(sample_image, qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr('subprocess.call', lambda *args, **kwargs: calls.append(args))
    if platform.system() == 'Windows':
        monkeypatch.setattr('os.startfile', lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr('webbrowser.open', lambda *args, **kwargs: calls.append(args))
    open_file(sample_image)
    assert len(calls) >= 1


def test_gui_image_view_initialization(sample_image, qtbot):
    image_view = GuiImageView(sample_image)
    qtbot.addWidget(image_view)
    assert image_view.file_path == sample_image
    assert image_view.image_label.pixmap() is not None
    assert image_view.width() == 250


def test_gui_image_view_click(sample_image, qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr('subprocess.call', lambda *args, **kwargs: calls.append(args))
    if platform.system() == 'Windows':
        monkeypatch.setattr('os.startfile', lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr('webbrowser.open', lambda *args, **kwargs: calls.append(args))
    image_view = GuiImageView(sample_image)
    qtbot.addWidget(image_view)
    qtbot.mouseClick(image_view, Qt.LeftButton)
    assert len(calls) >= 1


def test_gui_pdf_view_initialization(sample_pdf, qtbot):
    pdf_view = GuiPdfView(sample_pdf)
    qtbot.addWidget(pdf_view)
    assert pdf_view.file_path == sample_pdf
    assert pdf_view.document() is not None


def test_gui_pdf_view_click(sample_pdf, qtbot, monkeypatch):
    pdf_view = GuiPdfView(sample_pdf)
    pdf_view.setMinimumSize(200, 200)
    qtbot.addWidget(pdf_view)
    pdf_view.show()
    qtbot.waitExposed(pdf_view)
    assert pdf_view.document() is not None
    assert pdf_view.document().pageCount() > 0
    center = pdf_view.rect().center()
    if not pdf_view.rect().contains(center):
        pytest.skip("Widget too small for reliable clicking")
    qtbot.mousePress(pdf_view, Qt.LeftButton, pos=center)
    qtbot.mouseRelease(pdf_view, Qt.LeftButton, pos=center)


def test_gui_open_app_initialization(sample_image, qtbot):
    test_app = "test_app"
    open_app = GuiOpenApp(test_app, sample_image)
    qtbot.addWidget(open_app)
    assert open_app.file_path == sample_image
    assert open_app.app == test_app
    assert open_app.image_label.pixmap() is not None
    assert open_app.width() == 250


def test_gui_image_view_error_handling(tmp_path, qtbot):
    invalid_image = tmp_path / "invalid.png"
    invalid_image.write_text("not an image")
    with pytest.raises(RuntimeError):
        GuiImageView(str(invalid_image))


def test_gui_pdf_view_error_handling(tmp_path, qtbot):
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("not a pdf")
    with pytest.raises(RuntimeError):
        GuiPdfView(str(invalid_pdf))
