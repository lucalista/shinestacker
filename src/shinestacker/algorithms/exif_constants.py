IMAGEWIDTH = 256
IMAGELENGTH = 257
BITSPERSAMPLE = 258
COMPRESSION = 259
PHOTOMETRICINTERPRETATION = 262
IMAGEDESCRIPTION = 270
MAKE = 271
MODEL = 272
STRIPOFFSETS = 273
ORIENTATION = 274
SAMPLESPERPIXEL = 277
ROWSPERSTRIP = 278
STRIPBYTECOUNTS = 279
XRESOLUTION = 282
YRESOLUTION = 283
PLANARCONFIGURATION = 284
RESOLUTIONUNIT = 296
SOFTWARE = 305
DATETIME = 306
ARTIST = 315
PREDICTOR = 317
WHITEPOINT = 318
PRIMARYCHROMATICITIES = 319
COLORMAP = 320
TILEWIDTH = 322
TILELENGTH = 323
TILEOFFSETS = 324
TILEBYTECOUNTS = 325
EXIFIFD = 34665
ICCPROFILE = 34675
COPYRIGHT = 33432
EXPOSURETIME = 33434
FNUMBER = 33437
EXPOSUREPROGRAM = 34850
ISOSPEEDRATINGS = 34855
EXIFVERSION = 36864
DATETIMEORIGINAL = 36867
DATETIMEDIGITIZED = 36868
SHUTTERSPEEDVALUE = 37377
APERTUREVALUE = 37378
BRIGHTNESSVALUE = 37379
EXPOSUREBIASVALUE = 37380
MAXAPERTUREVALUE = 37381
SUBJECTDISTANCE = 37382
METERINGMODE = 37383
LIGHTSOURCE = 37384
FLASH = 37385
FOCALLENGTH = 37386
MAKERNOTE = 37500
USERCOMMENT = 37510
SUBSECTIME = 37520
SUBSECTIMEORIGINAL = 37521
SUBSECTIMEDIGITIZED = 37522
FLASHPIXVERSION = 40960
COLORSPACE = 40961
PIXELXDIMENSION = 40962
PIXELYDIMENSION = 40963
RELATEDSOUNDFILE = 40964
FLASHENERGY = 41483
SPATIALFREQUENCYRESPONSE = 41484
FOCALPLANEXRESOLUTION = 41486
FOCALPLANEYRESOLUTION = 41487
FOCALPLANERESOLUTIONUNIT = 41488
SUBJECTLOCATION = 41492
EXPOSUREINDEX = 41493
SENSINGMETHOD = 41495
FILESOURCE = 41728
SCENETYPE = 41729
CFAPATTERN = 41730
CUSTOMRENDERED = 41985
EXPOSUREMODE = 41986
WHITEBALANCE = 41987
DIGITALZOOMRATIO = 41988
FOCALLENGTHIN35MMFILM = 41989
SCENECAPTURETYPE = 41990
GAINCONTROL = 41991
CONTRAST = 41992
SATURATION = 41993
SHARPNESS = 41994
DEVICESETTINGDESCRIPTION = 41995
SUBJECTDISTANCERANGE = 41996
IMAGEUNIQUEID = 42016
LENSINFO = 42034
LENSMAKE = 42035
LENSMODEL = 42036
GPSIFD = 34853
XMLPACKET = 700
IMAGERESOURCES = 34377
INTERCOLORPROFILE = 34675

XMP_TEMPLATE = """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about='' xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:xmp='http://ns.adobe.com/xap/1.0/' xmlns:tiff='http://ns.adobe.com/tiff/1.0/' xmlns:exif='http://ns.adobe.com/exif/1.0/' xmlns:aux='http://ns.adobe.com/exif/1.0/aux/'>
    {content}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""  # noqa

XMP_EMPTY_TEMPLATE = """<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Adobe XMP Core 5.6-c140 79.160451, 2017/05/06-01:08:21'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=''/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""  # noqa

XMP_TO_EXIF_MAP = {
    'tiff:Make': MAKE,
    'tiff:Model': MODEL,
    'exif:ExposureTime': EXPOSURETIME,
    'exif:FNumber': FNUMBER,
    'exif:ISOSpeedRatings': ISOSPEEDRATINGS,
    'exif:FocalLength': FOCALLENGTH,
    'exif:DateTimeOriginal': DATETIMEORIGINAL,
    'xmp:CreateDate': DATETIME,
    'xmp:CreatorTool': SOFTWARE,
    'aux:Lens': LENSMODEL,  # Adobe's auxiliary namespace
    'exifEX:LensModel': LENSMODEL,  # EXIF 2.3 namespace
    'exif:Flash': FLASH,
    'exif:WhiteBalance': WHITEBALANCE,
    'dc:description': IMAGEDESCRIPTION,
    'dc:creator': ARTIST,
    'dc:rights': COPYRIGHT,
    'exif:ShutterSpeedValue': SHUTTERSPEEDVALUE,
    'exif:ApertureValue': APERTUREVALUE,
    'exif:ExposureBiasValue': EXPOSUREBIASVALUE,
    'exif:MaxApertureValue': MAXAPERTUREVALUE,
    'exif:MeteringMode': METERINGMODE,
    'exif:ExposureMode': EXPOSUREMODE,
    'exif:SceneCaptureType': SCENECAPTURETYPE
}


def safe_decode_bytes(data, encoding='utf-8'):
    if not isinstance(data, bytes):
        return data
    encodings = [encoding, 'latin-1', 'cp1252', 'utf-16', 'ascii']
    for enc in encodings:
        try:
            return data.decode(enc, errors='strict')
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


XMP_TAG_MAP = {
    IMAGEDESCRIPTION: {'format': 'dc:description', 'type': 'rdf_alt',
                       'processor': safe_decode_bytes},
    ARTIST: {'format': 'dc:creator', 'type': 'rdf_seq', 'processor': safe_decode_bytes},
    COPYRIGHT: {'format': 'dc:rights', 'type': 'rdf_alt', 'processor': safe_decode_bytes},
    MAKE: {'format': 'tiff:Make', 'type': 'simple', 'processor': safe_decode_bytes},
    MODEL: {'format': 'tiff:Model', 'type': 'simple', 'processor': safe_decode_bytes},
    DATETIME: {'format': 'xmp:CreateDate', 'type': 'datetime', 'processor': safe_decode_bytes},
    DATETIMEORIGINAL: {'format': 'exif:DateTimeOriginal', 'type': 'datetime',
                       'processor': safe_decode_bytes},
    SOFTWARE: {'format': 'xmp:CreatorTool', 'type': 'simple', 'processor': safe_decode_bytes},
    EXPOSURETIME: {'format': 'exif:ExposureTime', 'type': 'rational', 'processor': None},
    FNUMBER: {'format': 'exif:FNumber', 'type': 'rational', 'processor': None},
    ISOSPEEDRATINGS: {'format': 'exif:ISOSpeedRatings', 'type': 'rdf_seq', 'processor': None},
    FOCALLENGTH: {'format': 'exif:FocalLength', 'type': 'rational', 'processor': None},
    LENSMODEL: {'format': 'aux:Lens', 'type': 'simple', 'processor': safe_decode_bytes},
    SHUTTERSPEEDVALUE: {'format': 'exif:ShutterSpeedValue', 'type': 'rational', 'processor': None},
    APERTUREVALUE: {'format': 'exif:ApertureValue', 'type': 'rational', 'processor': None},
    EXPOSUREBIASVALUE: {'format': 'exif:ExposureBiasValue', 'type': 'rational', 'processor': None},
    MAXAPERTUREVALUE: {'format': 'exif:MaxApertureValue', 'type': 'rational', 'processor': None},
    METERINGMODE: {'format': 'exif:MeteringMode', 'type': 'simple', 'processor': None},
    FLASH: {'format': 'exif:Flash', 'type': 'simple', 'processor': None},
    WHITEBALANCE: {'format': 'exif:WhiteBalance', 'type': 'mapped', 'processor': None,
                   'map': {0: 'Auto', 1: 'Manual'}},
    EXPOSUREMODE: {'format': 'exif:ExposureMode', 'type': 'mapped', 'processor': None,
                   'map': {0: 'Auto', 1: 'Manual', 2: 'Auto bracket'}},
    SCENECAPTURETYPE: {'format': 'exif:SceneCaptureType', 'type': 'mapped', 'processor': None,
                       'map': {0: 'Standard', 1: 'Landscape', 2: 'Portrait', 3: 'Night scene'}}
}

CAMERA_TAGS_MAP = {
    MAKE: 'CameraMake',
    MODEL: 'CameraModel',
    SOFTWARE: 'Software',
    DATETIME: 'DateTime',
    ARTIST: 'Artist',
    COPYRIGHT: 'Copyright'
}

EXPOSURE_TAGS_MAP = {
    EXPOSURETIME: 'ExposureTime',
    FNUMBER: 'FNumber',
    ISOSPEEDRATINGS: 'ISOSpeedRatings',
    SHUTTERSPEEDVALUE: 'ShutterSpeedValue',
    APERTUREVALUE: 'ApertureValue',
    FOCALLENGTH: 'FocalLength',
    LENSMODEL: 'LensModel',
    EXPOSUREBIASVALUE: 'ExposureBiasValue',
    MAXAPERTUREVALUE: 'MaxApertureValue',
    METERINGMODE: 'MeteringMode',
    FLASH: 'Flash',
    WHITEBALANCE: 'WhiteBalance',
    EXPOSUREMODE: 'ExposureMode',
    SCENECAPTURETYPE: 'SceneCaptureType',
    DATETIMEORIGINAL: 'DateTimeOriginal'
}

EXPOSURE_DATA_TIFF = {v: k for k, v in EXPOSURE_TAGS_MAP.items()} | {
    'Make': MAKE,
    'Model': MODEL
}
