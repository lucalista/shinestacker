# pylint: disable=W0718, R0912, R0911
import re
from fractions import Fraction
from xml.dom import minidom
from PIL.TiffImagePlugin import IFDRational
from PySide6.QtWidgets import QLabel, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from .. algorithms.exif import exif_dict
from .. gui.config_dialog import ConfigDialog


class ExifData(ConfigDialog):
    DISPLAY_NAMES = {
        'Make': 'Camera Make',
        'Model': 'Camera Model',
        'DateTime': 'Date/Time',
        'FNumber': 'F-Number',
        'ISOSpeedRatings': 'ISO Speed',
        'ShutterSpeedValue': 'Shutter Speed',
        'ApertureValue': 'Aperture',
        'ExposureBiasValue': 'Exposure Bias',
        'MaxApertureValue': 'Max Aperture',
        'DateTimeOriginal': 'Original Date/Time',
        'DateTimeDigitized': 'Digitized Date/Time',
        'ExifVersion': 'EXIF Version',
        'CompressedBitsPerPixel': 'Compressed Bits/Pixel',
        'ExifImageWidth': "EXIF Image Width",
        'ExifImageHeight': "EXIF Image Height",
        'BitsPerSample': "Bits per Sample",
        'SubsamplesPerPixel': "Subsamples per Pixel",
        'SamplesPerPixel': "Samples per Pixel",
        'RowsPerStrip': 'Rows per Strip',
        'ExifOffset': "EXIF Offset",
        'InterColorProfile': "Inter-Color Profile",
    }

    def __init__(self, exif, title="EXIF Data", parent=None, show_buttons=True):
        self.exif = exif
        super().__init__(title, parent)
        self.reset_button.setVisible(False)
        self.cancel_button.setVisible(show_buttons)
        if not show_buttons:
            self.ok_button.setFixedWidth(100)
            self.button_box.setAlignment(Qt.AlignCenter)

    def format_tag_name(self, tag_name):
        if tag_name in self.DISPLAY_NAMES:
            return self.DISPLAY_NAMES[tag_name]
        formatted = re.sub(r'(?<=[a-zA-Z])(?=[A-Z][a-z])', ' ', tag_name)
        return formatted

    def format_aperture(self, value):
        if isinstance(value, IFDRational):
            if value.denominator == 0:
                return "f/>1024"
            aperture_value = value.numerator / value.denominator
            return f"f/{aperture_value:.1f}"
        if isinstance(value, (int, float)):
            return f"f/{float(value):.1f}"
        return str(value)

    def format_exposure_time(self, value):
        if isinstance(value, IFDRational):
            exposure_time = value.numerator / value.denominator
        elif isinstance(value, (int, float)):
            exposure_time = float(value)
        else:
            return str(value)
        if exposure_time >= 0.5:
            return f"{exposure_time:.1f} s"
        if isinstance(value, IFDRational):
            return f"{value.numerator}/{value.denominator} s"
        frac = Fraction(exposure_time).limit_denominator(1000)
        return f"{frac.numerator}/{frac.denominator} s"

    def format_date_time(self, value):
        if not isinstance(value, str):
            return str(value)
        try:
            if ':' in value and ' ' in value:
                date_part, time_part = value.split(' ', 1)
                year, month, day = date_part.split(':', 2)
                return f"{day}/{month}/{year} {time_part}"
            return value
        except (ValueError, IndexError):
            return value

    def format_iso_speed(self, value):
        if isinstance(value, (int, float)):
            return f"ISO {int(value)}"
        if isinstance(value, str):
            try:
                return f"ISO {int(value)}"
            except ValueError:
                return value
        return str(value)

    def format_focal_length(self, value):
        if isinstance(value, IFDRational):
            focal_length = value.numerator / value.denominator
            return f"{focal_length:.1f} mm"
        if isinstance(value, (int, float)):
            return f"{float(value):.1f} mm"
        return str(value)

    def is_likely_xml(self, text):
        if not isinstance(text, str):
            return False
        text = text.strip()
        return (text.startswith('<?xml') or
                text.startswith('<x:xmpmeta') or
                text.startswith('<rdf:RDF') or
                text.startswith('<?xpacket') or
                (text.startswith('<') and text.endswith('>') and
                 any(tag in text for tag in ['<rdf:', '<xmp:', '<dc:', '<tiff:'])))

    def prettify_xml(self, xml_string):
        try:
            parsed = minidom.parseString(xml_string)
            pretty_xml = parsed.toprettyxml(indent="  ")
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            if lines and lines[0].startswith('<?xml version="1.0" ?>'):
                lines = lines[1:]
            return '\n'.join(lines)
        except Exception:
            return xml_string

    def format_value(self, tag_name, value):
        if tag_name in ['FNumber', 'ApertureValue', 'MaxApertureValue']:
            return self.format_aperture(value)
        if tag_name in ['ExposureTime', 'ShutterSpeedValue']:
            return self.format_exposure_time(value)
        if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
            return self.format_date_time(value)
        if tag_name == 'ISOSpeedRatings':
            return self.format_iso_speed(value)
        if tag_name == 'FocalLength':
            return self.format_focal_length(value)
        if isinstance(value, IFDRational):
            return f"{value.numerator}/{value.denominator}"
        return str(value)

    def create_form_content(self):
        if self.exif is None:
            data = {}
        else:
            data = exif_dict(self.exif)
        if len(data) > 0:
            for tag_name, (_, value) in data.items():
                display_name = self.format_tag_name(tag_name)
                display_value = self.format_value(tag_name, value)
                value_str = display_value
                if "<<<" not in value_str and tag_name != 'IPTCNAA':
                    if len(value_str) <= 40:
                        self.container_layout.addRow(f"<b>{display_name}:</b>", QLabel(value_str))
                    else:
                        if self.is_likely_xml(value_str):
                            value_str = self.prettify_xml(value_str)
                        text_edit = QTextEdit()
                        text_edit.setPlainText(value_str)
                        text_edit.setReadOnly(True)
                        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
                        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        text_edit.setFixedWidth(400)
                        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
                        font.setPointSize(10)
                        text_edit.setFont(font)
                        text_edit.setFixedHeight(200)
                        text_edit.setFixedHeight(100)
                        self.container_layout.addRow(f"<b>{display_name}:</b>", text_edit)
        else:
            self.container_layout.addRow("No EXIF Data", QLabel(''))
