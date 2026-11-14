import numpy as np
import pytest
from shinestacker.algorithms.stack_framework import StackJob
from shinestacker.algorithms import stack as stack_module
from shinestacker.algorithms.stack import (
    FocusStack, FocusStackBunch, extract_frame_identifiers, get_bunches)
from shinestacker.core.exceptions import InvalidOptionError
from shinestacker.algorithms.pyramid import PyramidStack
from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack
from shinestacker.algorithms.pyramid_auto import PyramidAutoStack
from shinestacker.algorithms.depth_map import DepthMapStack


def test_jpg():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_filter():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  denoise_amount=0.1, sharpen_amount_percent=10,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "examples", input_path="input/img-tif")
        job.add_action(FocusStack("stack-pyramid-tiff", PyramidStack(),
                                  output_path="output/img-tif-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='dm_'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm_plot():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(plot_depth_map=True),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='dm_'))
        job.run()
    except Exception:
        assert False


def test_jpg_pt_1():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidTilesStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_pt_2():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidTilesStack(max_threads=1),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_auto_1():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidAutoStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_auto_2():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidAutoStack(memory_limit=0.2),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_bunches():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                                       output_path="output/img-jpg-bunches",
                                       delete_output_at_end=True,
                                       frames=3))
        job.run()
    except Exception:
        assert False


def test_jpg_template():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  output_file_template="{method}_{input_count}frames_stack"))
        job.run()
    except Exception:
        assert False


def test_bunches_template():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(
            FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                            output_path="output/img-jpg-bunches",
                            delete_output_at_end=True, frames=3,
                            output_file_template="{method}_{input_count}"
                            "frames_bunch-{bunch_index:03d}"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_jpg()
    test_jpg_filter()
    test_tif()
    test_jpg_dm()
    test_jpg_dm_plot()
    test_jpg_pt_1()
    test_jpg_pt_2()
    test_jpg_auto_1()
    test_jpg_auto_2()
    test_bunches()
    test_jpg_template()
    test_bunches_template()


def test_tif_icc_profile_without_exif(tmp_path):
    import numpy as np
    import tifffile
    from PIL import ImageCms
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    (tmp_path / "input").mkdir()
    rng = np.random.default_rng(1)
    for i in range(3):
        img = rng.integers(0, 65535, size=(64, 96, 3), dtype=np.uint16)
        tifffile.imwrite(tmp_path / "input" / f"{i:04d}.tif", img, photometric='rgb',
                         iccprofile=profile)
    job = StackJob("job", str(tmp_path), input_path="input")
    job.add_action(FocusStack("stack", DepthMapStack(), output_path="output", prefix='dm_'))
    job.run()
    outputs = list((tmp_path / "output").glob("*.tif"))
    assert len(outputs) == 1
    with tifffile.TiffFile(outputs[0]) as tif:
        assert tif.pages[0].iccprofile == profile


def test_tif_icc_profile_through_intermediate_frames(tmp_path):
    """Frames written by CombinedActions (alignment, balancing) keep the input's
    profile, so a stack made from them in a second job still carries it."""
    import numpy as np
    import tifffile
    from PIL import ImageCms
    from shinestacker.algorithms.stack_framework import CombinedActions, SubAction

    class Identity(SubAction):
        def run_frame(self, _idx, _ref_idx, image):
            return image

    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    (tmp_path / "input").mkdir()
    rng = np.random.default_rng(1)
    for i in range(3):
        img = rng.integers(0, 65535, size=(64, 96, 3), dtype=np.uint16)
        tifffile.imwrite(tmp_path / "input" / f"{i:04d}.tif", img, photometric='rgb',
                         iccprofile=profile)
    job = StackJob("align", str(tmp_path), input_path="input")
    job.add_action(CombinedActions("aligned", [Identity()]))
    job.run()
    for f in (tmp_path / "aligned").glob("*.tif"):
        with tifffile.TiffFile(f) as tif:
            assert tif.pages[0].iccprofile == profile
        assert np.array_equal(tifffile.imread(f), tifffile.imread(tmp_path / "input" / f.name))
    job = StackJob("stack", str(tmp_path), input_path="aligned")
    job.add_action(FocusStack("stack", DepthMapStack(), output_path="output", prefix='dm_'))
    job.run()
    outputs = list((tmp_path / "output").glob("*.tif"))
    assert len(outputs) == 1
    with tifffile.TiffFile(outputs[0]) as tif:
        assert tif.pages[0].iccprofile == profile


def test_bunches_description_counts_original_frames():
    import glob
    from PIL import Image
    job = StackJob("job", "examples", input_path="input/img-jpg")
    job.add_action(FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                                   output_path="output/img-jpg-bunches-descr",
                                   frames=3, overlap=1))
    job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                              output_path="output/img-jpg-stack-descr",
                              exif_path="input/img-jpg", prefix="descr_"))
    job.run()
    n_input = len(glob.glob("examples/input/img-jpg/*.jpg"))
    assert len(glob.glob("examples/output/img-jpg-bunches-descr/*.jpg")) < n_input
    outputs = glob.glob("examples/output/img-jpg-stack-descr/descr_*.jpg")
    assert len(outputs) == 1
    description = Image.open(outputs[0]).getexif().get(270)
    assert description == f"Image generated with ShineStacker from {n_input} frames"


def _reference_local_stats(image, probabilities, pad, float_type):
    padded = np.pad(image, pad, mode='reflect')
    entropy = np.zeros(image.shape, dtype=float_type)
    deviation = np.zeros(image.shape, dtype=float_type)
    for r in range(image.shape[0]):
        for c in range(image.shape[1]):
            area = padded[r:r + 2 * pad + 1, c:c + 2 * pad + 1]
            levels = area.flatten()
            entropy[r, c] = -(levels * np.log(probabilities[levels])).sum()
            deviation[r, c] = np.square(area - np.average(area)).sum() / area.size
    return entropy, deviation


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
@pytest.mark.parametrize("float_type", ['float-32', 'float-64'])
def test_pyramid_entropy_deviation_match_reference(dtype, float_type):
    algo = PyramidStack(float_type=float_type)
    algo.dtype = dtype
    max_value = np.iinfo(dtype).max
    rng = np.random.default_rng(0)
    image = rng.integers(0, max_value // 8, (17, 23)).astype(dtype)
    levels, counts = np.unique(image, return_counts=True)
    probabilities = np.zeros(max_value + 1)
    probabilities[levels] = counts / counts.sum()
    ref_entropy, ref_deviation = _reference_local_stats(
        image, probabilities, algo.pad_amount, algo.float_type)
    rtol = 1e-4 if algo.float_type == np.float32 else 1e-9
    assert algo.entropy(image).dtype == algo.float_type
    np.testing.assert_allclose(algo.entropy(image), ref_entropy, rtol=rtol)
    np.testing.assert_allclose(algo.deviation(image), ref_deviation, rtol=rtol, atol=1e-6)


@pytest.mark.parametrize(
    "names, expected",
    [([], ("", "", [])),
     (["a.jpg"], ("", "", ["a.jpg"])),
     (["one-a.jpg", "two-a.jpg"], ("", "-a.jpg", ["one", "two"])),
     (["frame-1.jpg", "frame-2.jpg"], ("frame-", ".jpg", ["1", "2"])),
     (["frame-a", "frame-b"], ("frame-", "", ["a", "b"])),
     (["one", "two"], ("", "", ["one", "two"]))],
)
def test_extract_frame_identifiers(names, expected):
    assert extract_frame_identifiers(names) == expected


def test_bunch_validation_and_partial_final_bunch():
    assert get_bunches([1, 2], 3, 1) == [[1, 2]]
    assert get_bunches([1, 2, 3, 4], 3, 1) == [[1, 2, 3], [3, 4]]
    with pytest.raises(RuntimeError, match="equal"):
        get_bunches([1, 2], 2, 2)
    with pytest.raises(InvalidOptionError):
        FocusStackBunch("stack", PyramidStack(), frames=2, overlap=2)


def test_output_naming_and_bunch_indices():
    action = FocusStack("stack", PyramidStack(), naming_mode="TEMPLATE",
                        output_file_template="{method}_{input_prefix}{input_min}-{input_max}"
                                             "_{input_count}")
    action._input_filepaths = ["/input/img-01.jpg", "/input/img-02.jpg"]
    assert action.resolve_output_filename("first.jpg") == "pyramid_img-01-2_2.jpg"
    bunch = FocusStackBunch("bunch", PyramidStack(), naming_mode="TEMPLATE",
                            output_file_template="stack_{bunch_index}")
    bunch._input_filepaths = action._input_filepaths
    bunch.bunch_index = 4
    assert bunch.resolve_output_filename("frame.tif") == "stack_4.tif"
    bunch.output_file_template = "stack_{bunch_index:03d}"
    assert bunch.resolve_output_filename("frame.tif") == "stack_004.tif"


@pytest.mark.parametrize(
    "names, input_name, expected",
    [([], "input.jpg", None),
     (["a.nef", "b.tif", "c.jpg"], "input.jpg", "c.jpg"),
     (["a.nef", "b.tif"], "input.jpg", "b.tif"),
     (["a.nef", "b.nef"], "input.jpg", "a.nef")],
)
def test_first_source_file_selection(tmp_path, names, input_name, expected):
    for name in names:
        (tmp_path / name).touch()
    result = FocusStack.first_source_file(str(tmp_path), [input_name])
    assert result == (str(tmp_path / expected) if expected else None)
    assert FocusStack.first_source_file(str(tmp_path / "missing"), [input_name]) is None


@pytest.mark.parametrize(
    "source_names, expected",
    [(["a.nef", "b.tif", "c.jpg"], "c.jpg"),
     (["a.nef", "b.tif"], "b.tif"),
     (["a.nef", "b.nef"], "a.nef")],
)
def test_focus_stack_selects_exif_source(tmp_path, monkeypatch, source_names, expected):
    from PIL import Image

    input_file = tmp_path / "input.jpg"
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(input_file)
    exif_dir = tmp_path / "exif"
    exif_dir.mkdir()
    for name in source_names:
        (exif_dir / name).touch()
    copied = []
    monkeypatch.setattr(stack_module, 'copy_exif_from_file_to_file',
                        lambda *args, **kwargs: copied.append((args, kwargs)))
    action = FocusStack("stack", PyramidStack(), working_path=str(tmp_path), output_path=".",
                        exif_path=str(exif_dir), denoise_amount=0, sharpen_amount_percent=0)
    action.focus_stack([str(input_file)])
    assert len(copied) == 1
    assert copied[0][0][0] == str(exif_dir / expected)
    assert copied[0][1]['description'].endswith('1 frame')


def test_focus_stack_16bit_png_skips_exif(tmp_path, monkeypatch):
    input_file = tmp_path / "input.png"
    monkeypatch.setattr(stack_module, 'read_img',
                        lambda _: np.zeros((8, 8, 3), dtype=np.uint16))
    output = []
    monkeypatch.setattr(stack_module, 'write_img',
                        lambda *args, **kwargs: output.append((args, kwargs)))
    monkeypatch.setattr(stack_module, 'copy_exif_from_file_to_file',
                        lambda *args, **kwargs: pytest.fail("EXIF should not be copied"))
    action = FocusStack("stack", PyramidStack(), working_path=str(tmp_path), output_path=".",
                        exif_path="unused", denoise_amount=0, sharpen_amount_percent=0)
    messages = []
    monkeypatch.setattr(action, 'sub_message_r',
                        lambda message, **kwargs: messages.append(message))
    action.focus_stack([str(input_file)])
    assert output[0][0][1].dtype == np.uint16
    assert any("exif not supported for 16-bit PNG" in message for message in messages)


@pytest.mark.parametrize("exif_dir_exists", [False, True])
def test_focus_stack_reports_missing_exif_sources(tmp_path, monkeypatch, exif_dir_exists):
    input_file = tmp_path / "input.jpg"
    exif_dir = tmp_path / "exif"
    if exif_dir_exists:
        exif_dir.mkdir()
    monkeypatch.setattr(stack_module, 'read_img',
                        lambda _: np.zeros((8, 8, 3), dtype=np.uint8))
    monkeypatch.setattr(stack_module, 'write_img', lambda *args, **kwargs: None)
    action = FocusStack("stack", PyramidStack(), working_path=str(tmp_path), output_path=".",
                        exif_path=str(exif_dir), denoise_amount=0, sharpen_amount_percent=0)
    messages = []
    monkeypatch.setattr(action, 'sub_message_r',
                        lambda message, **kwargs: messages.append(message))
    if exif_dir_exists:
        action.focus_stack([str(input_file)])
        assert any("does not contain image files" in message for message in messages)
    else:
        with pytest.raises(RuntimeError, match="does not exist"):
            action.focus_stack([str(input_file)])


def test_register_source_frames_deduplicates_intermediate_inputs(tmp_path):
    action = FocusStack("stack", PyramidStack())
    source_a, source_b = str(tmp_path / "a.jpg"), str(tmp_path / "b.jpg")
    intermediate = str(tmp_path / "intermediate.jpg")
    output = str(tmp_path / "output.jpg")
    assert action.register_source_frames([source_a, source_b], intermediate) == 2
    assert action.register_source_frames([source_a, intermediate], output) == 2
    assert action.frame_sources[output] == frozenset([source_a, source_b])
