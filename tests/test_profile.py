import time
import datetime
import importlib

import boto3
from moto import mock_xray_client, XRaySegment


@mock_xray_client
def test_xray_tracing(caplog):
    from terracotta import update_settings
    import terracotta.profile

    update_settings(XRAY_PROFILE=True)

    @terracotta.profile.trace()
    def func_to_trace():
        time.sleep(0.1)

    with XRaySegment():
        func_to_trace()

    with XRaySegment():
        with terracotta.profile.trace():
            time.sleep(0.1)

    for record in caplog.records:
        assert record.levelname != 'ERROR'

    # sanity check, recording without starting a segment should fail
    func_to_trace()
    assert any(
        ('cannot find the current segment' in record.message)
        and (record.levelname == 'ERROR') for record in caplog.records
    )
