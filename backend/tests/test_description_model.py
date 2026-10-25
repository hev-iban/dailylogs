"""Direct tests of the DescriptionIn model and its mapping to the 422 details."""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.datastructures import UploadFile

import models
from conftest import assert_nothing_stored
from routes import _validate_description

BLANK = "description is required and cannot be blank"
TOO_LONG = "description must be at most 200 characters"


def test_model_trims_and_counts_code_points():
    assert models.DescriptionIn(description="  hi \n").description == "hi"
    assert len(models.DescriptionIn(description="\U0001F600" * 200).description) == 200
    with pytest.raises(ValidationError):
        models.DescriptionIn(description="\U0001F600" * 201)


@pytest.mark.parametrize("value", [None, b"abc", 5, UploadFile(file=None)])
def test_non_string_maps_to_blank_message(value):
    with pytest.raises(HTTPException) as err:
        _validate_description(value)
    assert (err.value.status_code, err.value.detail) == (422, BLANK)


def test_blank_description_beats_oversized_photo_detail(env):
    client, db, uploads = env
    big = b"\0" * (models.MAX_PHOTO_BYTES + 1)
    resp = client.post("/api/logs", data={"description": "   "},
                       files=[("photos", ("p.png", big, "image/png"))])
    assert (resp.status_code, resp.json()) == (422, {"detail": BLANK})
    assert_nothing_stored(db, uploads)
