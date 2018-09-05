import pytest


def test_default_transform():
    from rasterio.warp import calculate_default_transform
    from rasterio._err import CPLE_OutOfMemoryError

    from terracotta.drivers.raster_base import RasterDriver

    args = (
        'epsg:4326',
        'epsg:4326',
        2 * 10**6,
        10**6,
        -10, -10, 10, 10
    )

    # we can handle cases rasterio can't
    with pytest.raises(CPLE_OutOfMemoryError):
        rio_transform, rio_width, rio_height = calculate_default_transform(*args)

    our_transform, our_width, our_height = RasterDriver._calculate_default_transform(*args)

    assert our_width == args[2]
    assert our_height == args[3]


@pytest.mark.parametrize('use_chunks', [True, False])
def test_compute_metadata(big_raster_file, use_chunks):
    import rasterio
    import rasterio.features
    from shapely.geometry import shape
    import numpy as np

    from terracotta.drivers.raster_base import RasterDriver

    with rasterio.open(str(big_raster_file)) as src:
        data = src.read(1)
        valid_data = data[np.isfinite(data) & (data != src.nodata)]
        dataset_shape = list(rasterio.features.dataset_features(
            src, bidx=1, as_mask=True, geographic=True
        ))

    convex_hull = shape(dataset_shape[0]['geometry']).convex_hull

    # compare
    mtd = RasterDriver.compute_metadata(str(big_raster_file), use_chunks=use_chunks)

    np.testing.assert_allclose(mtd['valid_percentage'], 100 * valid_data.size / data.size)
    np.testing.assert_allclose(mtd['range'], (valid_data.min(), valid_data.max()))
    np.testing.assert_allclose(mtd['mean'], valid_data.mean())
    np.testing.assert_allclose(mtd['stdev'], valid_data.std())

    # allow error of 1%, since we only compute approximate quantiles
    np.testing.assert_allclose(
        mtd['percentiles'], 
        np.percentile(valid_data, np.arange(1, 100)),
        rtol=0.01
    )

    assert shape(mtd['convex_hull']).equals(convex_hull)


@pytest.mark.parametrize('use_chunks', [True, False])
def test_compute_metadata_invalid(invalid_raster_file, use_chunks):
    from terracotta.drivers.raster_base import RasterDriver

    with pytest.raises(ValueError):
        RasterDriver.compute_metadata(str(invalid_raster_file), use_chunks=use_chunks)


def test_compute_metadata_nocrick(big_raster_file):
    import importlib

    import rasterio
    import rasterio.features
    from shapely.geometry import shape
    import numpy as np

    with rasterio.open(str(big_raster_file)) as src:
        data = src.read(1)
        valid_data = data[np.isfinite(data) & (data != src.nodata)]
        dataset_shape = list(rasterio.features.dataset_features(
            src, bidx=1, as_mask=True, geographic=True
        ))

    convex_hull = shape(dataset_shape[0]['geometry']).convex_hull

    import terracotta.drivers.raster_base
    terracotta.drivers.raster_base.has_crick = False

    with pytest.warns(UserWarning):
        mtd = terracotta.drivers.raster_base.RasterDriver.compute_metadata(
            str(big_raster_file), use_chunks=True)  

    # compare
    np.testing.assert_allclose(mtd['valid_percentage'], 100 * valid_data.size / data.size)
    np.testing.assert_allclose(mtd['range'], (valid_data.min(), valid_data.max()))
    np.testing.assert_allclose(mtd['mean'], valid_data.mean())
    np.testing.assert_allclose(mtd['stdev'], valid_data.std())

    # allow error of 1%, since we only compute approximate quantiles
    np.testing.assert_allclose(
        mtd['percentiles'],
        np.percentile(valid_data, np.arange(1, 100)),
        rtol=0.01
    )

    assert shape(mtd['convex_hull']).equals(convex_hull)
